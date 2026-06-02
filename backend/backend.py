import os
import re
import shutil
import requests
import subprocess
from flask import Flask, jsonify, request

app = Flask(__name__)

BACKUP_DIRECTORY = "/backups"
LOG_DIRECTORY = "/logs"
DROPBOX_PATH = "/Documents/Vaultwarden/Backups"

MAILGUN_API_KEY = os.environ["MAILGUN_API_KEY"]
MAILGUN_DOMAIN = "mail.lukeleiby.com"
MAILGUN_API_BASE = f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}"

EMAIL_TO = os.environ["EMAIL_TO"]

SEND_EMAIL_NOTIFICATION = os.environ["SEND_EMAIL_NOTIFICATION"]
SYNC_BACKUPS_TO_DROPBOX = os.environ["SYNC_BACKUPS_TO_DROPBOX"]


def loadTemplate(templateName):
    templatePath = os.path.join("/app/email_templates", templateName)

    with open(templatePath, "r") as file:
        return file.read()


def renderTemplate(templateStr, **kwargs):
    return templateStr.format(**kwargs)


def extractBackupPath(logId):
    logPath = f"{LOG_DIRECTORY}/{logId}/app.log"

    with open(logPath, "r") as f:
        content = f.read()

    match = re.search(r"(/backups/[^\"\s']+\.tar\.xz\.gpg)", content)

    if not match:
        raise RuntimeError("Backup path not found in log file")

    return match.group(1)


def renameBackup(backupPath):
    baseName = os.path.basename(backupPath)

    match = re.match(
        r"(\d{4}-\d{2}-\d{2})-(\d{2})(\d{2})(\d{2})_backup\.tar\.xz\.gpg$", baseName
    )

    if not match:
        raise RuntimeError(f"Unexpected filename format: {baseName}")

    datePart, hour, minute, second = match.groups()

    newName = f"{datePart}T{hour}-{minute}-{second}Z_backup.tar.xz.gpg"
    newPath = os.path.join(BACKUP_DIRECTORY, newName)

    os.rename(backupPath, newPath)

    return newName


def deleteLogDirectory(logId):
    logDir = f"{LOG_DIRECTORY}/{logId}"

    if os.path.exists(logDir):
        shutil.rmtree(logDir)


def syncBackupsToDropbox():
    subprocess.run(
        [
            "rclone",
            "sync",
            BACKUP_DIRECTORY,
            f"dropbox:{DROPBOX_PATH}",
        ],
        check=True,
    )


def sendEmail(subject, body):
    requests.post(
        f"{MAILGUN_API_BASE}/messages",
        auth=("api", MAILGUN_API_KEY),
        data={
            "from": "Vaultwarden Backup Alerts <notifications@mail.lukeleiby.com>",
            "to": EMAIL_TO,
            "subject": subject,
            "text": body,
        },
    )


@app.route("/success", methods=["GET", "POST"])
def success():
    logId = request.values.get("logId")

    if not logId:
        return jsonify({"status": "error", "message": "missing logId"}), 400

    try:
        backupPath = extractBackupPath(logId)
        newName = renameBackup(backupPath)

        if SYNC_BACKUPS_TO_DROPBOX == "true":
            syncBackupsToDropbox()

        deleteLogDirectory(logId)

        if SEND_EMAIL_NOTIFICATION == "true":
            templateStr = loadTemplate("success.txt")
            body = renderTemplate(templateStr, dropboxPath=f"{DROPBOX_PATH}/{newName}")

            sendEmail("Successful Vaultwarden Backup Notification", body)

        return jsonify({"status": "success", "backup": newName}), 200

    except Exception as e:
        templateStr = loadTemplate("failure.txt")
        body = renderTemplate(
            templateStr,
            error=str(e),
        )

        sendEmail("Failed Vaultwarden Backup Notification", body)

        return jsonify({"status": "failure", "message": str(e)}), 500


@app.route("/failure", methods=["GET", "POST"])
def failure():
    templateStr = loadTemplate("failure.txt")
    body = renderTemplate(
        templateStr, error="The backup container failed to create a backup"
    )

    sendEmail("Failed Vaultwarden Backup Notification", body)

    return jsonify(
        {
            "status": "failure",
            "message": "The backup container failed to create a backup",
        }
    ), 200
