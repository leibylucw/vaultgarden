#!/usr/bin/env bash

logId="$(openssl rand -hex 8)"
logDirectory="/logs/$logId"

backupCommand=(
	docker compose run --rm
	-e "LOG_DIR=$logDirectory"
	vaultwarden-backup
	manual
)

cd ~/bitwarden

postLog() {
	local status="$1"

	curl -X POST \
		-d "logId=$logId" \
		"http://localhost:6284/$status"
}

if "${backupCommand[@]}"; then
	postLog "success"
else
	postLog "failure"
fi
