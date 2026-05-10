# Sarvam AI Proxy

A thin proxy that makes the [Sarvam AI API](https://docs.sarvam.ai) compatible with the OpenAI SDK / AI SDK client libraries.

## What it does

Some AI SDKs send `messages[].content` as an array of `{type, text}` parts (e.g. `[{type: "text", text: "Hello"}, {type: "image_url", ...}]`). Sarvam's API expects a plain string. This proxy flattens those arrays by concatenating text parts and stripping image parts, then forwards the request to `api.sarvam.ai`.

It also serves `GET /models` for model discovery, which OpenAI-compatible clients call on init.

## Usage

Point your client at the proxy URL (no `/v1` needed — the proxy adds it automatically).

### Python (local)

```bash
SARVAM_API_KEY=sk_xxx python3 sarvam-proxy.py
# Client → http://localhost:4040
```

### Cloudflare Worker (deployed)

```bash
cd worker && wrangler deploy
# Client → https://sarvam-proxy.<your-subdomain>.workers.dev
```

## Deployments

| Type | URL |
|------|-----|
| Cloudflare Worker | `https://sarvam-proxy.aswincveli.workers.dev` |
| Local Python | `http://localhost:4040` |
