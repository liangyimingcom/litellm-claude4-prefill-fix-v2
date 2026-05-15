FROM ghcr.io/berriai/litellm:main-latest

COPY custom_callbacks.py /app/custom_callbacks.py
COPY config.yaml /app/config.yaml

EXPOSE 4000

CMD ["--config", "/app/config.yaml", "--port", "4000"]
