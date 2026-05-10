const UPSTREAM = "https://api.sarvam.ai";

interface ContentPart {
  type?: string;
  text?: string;
  image_url?: unknown;
}

function flattenContent(value: unknown): string {
  if (typeof value === "string") return value;
  if (Array.isArray(value)) {
    const parts: string[] = [];
    for (const part of value) {
      if (part && typeof part === "object") {
        const p = part as ContentPart;
        if (p.type === "text") parts.push(p.text ?? "");
        else if (p.type === "image_url") parts.push("[image]");
      }
    }
    return parts.join("").trim();
  }
  return value != null ? String(value) : "";
}

function normalizeBody(body: Record<string, unknown>): Record<string, unknown> {
  if (!Array.isArray(body.messages)) return body;
  return {
    ...body,
    messages: body.messages.map((msg: unknown) => {
      const m = msg as Record<string, unknown>;
      if (m.content !== undefined) {
        return { ...m, content: flattenContent(m.content) };
      }
      return m;
    }),
  };
}

const MODELS = [
  { id: "sarvam-105b", object: "model", created: 1700000000, owned_by: "sarvam" },
  { id: "sarvam-30b", object: "model", created: 1700000001, owned_by: "sarvam" },
  { id: "sarvam-m", object: "model", created: 1700000002, owned_by: "sarvam" },
];

export default {
  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);
    const auth = request.headers.get("Authorization");

    // OpenAI-compatible clients call GET /models or /v1/models on init
    if (request.method === "GET" && (url.pathname === "/v1/models" || url.pathname === "/models")) {
      return new Response(JSON.stringify({ object: "list", data: MODELS }), {
        headers: { "Content-Type": "application/json" },
      });
    }

    if (request.method !== "POST") {
      return new Response("method not allowed", { status: 405 });
    }

    let body: Record<string, unknown>;
    try {
      body = normalizeBody(await request.json());
    } catch {
      return new Response("invalid json", { status: 400 });
    }

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (auth) headers["Authorization"] = auth;

    // Prepend /v1 when the client omits it (e.g. /chat/completions -> /v1/chat/completions)
    const upstreamPath = url.pathname.startsWith("/v1/") ? url.pathname : `/v1${url.pathname}`;
    const resp = await fetch(UPSTREAM + upstreamPath, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });

    return new Response(resp.body, {
      status: resp.status,
      headers: resp.headers,
    });
  },
};
