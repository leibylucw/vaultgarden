# Builder stage (rclone only)
FROM alpine:3.20 AS builder

ARG RCLONE_VERSION=v1.68.2
ARG TARGETARCH

RUN apk add --no-cache curl unzip ca-certificates

RUN curl -fsSL -o /tmp/rclone.zip \
	https://downloads.rclone.org/${RCLONE_VERSION}/rclone-${RCLONE_VERSION}-linux-${TARGETARCH}.zip && \
	unzip /tmp/rclone.zip -d /tmp && \
	install /tmp/rclone-*/rclone /usr/local/bin/rclone && \
	rm -rf /tmp/rclone*

# Runtime stage
FROM ghcr.io/astral-sh/uv:python3.12-alpine

ENV UV_CACHE_DIR=/app/.uv-cache
ENV UV_LINK_MODE=copy
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=/app/backend.py

COPY --from=builder /usr/local/bin/rclone /usr/local/bin/rclone

# Create directories owned by the non-root user
RUN mkdir -p /app /uv/.cache && \
	chown -R 999:999 /app /uv/.cache

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --locked

COPY backend.py ./
COPY email_templates/ ./email_templates/

RUN chown -R 999:999 /app

USER 999:999

ENTRYPOINT ["uv", "run"]
CMD ["flask", "run", "--debug", "--host=0.0.0.0", "--port=5000"]
