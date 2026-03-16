import OpenAI, { AzureOpenAI } from "openai";

export type ReasoningEffort = "low" | "medium" | "high";

// ---------------------------------------------------------------------------
// Azure OpenAI configuration helpers
// ---------------------------------------------------------------------------

interface AzureConfig {
  apiKey: string;
  endpoint: string;
  deployment: string;
  apiVersion: string;
}

function getAzureConfig(): AzureConfig | null {
  const apiKey = process.env.AZURE_OPENAI_API_KEY?.trim();
  const endpoint = process.env.AZURE_OPENAI_ENDPOINT?.trim();
  const deployment = process.env.AZURE_OPENAI_DEPLOYMENT?.trim();
  if (!apiKey || !endpoint || !deployment) return null;
  return {
    apiKey,
    endpoint,
    deployment,
    apiVersion:
      process.env.AZURE_OPENAI_API_VERSION?.trim() ?? "2025-01-01-preview",
  };
}

function isReasoningModel(deployment: string): boolean {
  return /^o[134]/i.test(deployment);
}

// ---------------------------------------------------------------------------
// Vanilla OpenAI key resolver (backup path)
// ---------------------------------------------------------------------------

function resolveApiKey(overrideApiKey?: string): string {
  const apiKey = overrideApiKey?.trim() || process.env.OPENAI_API_KEY?.trim();
  if (!apiKey) {
    throw new Error(
      "Missing OpenAI API key. Set OPENAI_API_KEY or provide api_key in request.",
    );
  }
  return apiKey;
}

// ---------------------------------------------------------------------------
// Token estimation helpers
// ---------------------------------------------------------------------------

export function estimateTokens(text: string): number {
  // Rough heuristic used for fast gating/cost estimates in serverless.
  return Math.ceil(text.length / 4);
}

// ---------------------------------------------------------------------------
// Streaming
// ---------------------------------------------------------------------------

interface StreamCompletionParams {
  model: string;
  systemPrompt: string;
  userPrompt: string;
  apiKey?: string;
  reasoningEffort?: ReasoningEffort;
  maxOutputTokens?: number;
}

export async function* streamCompletion({
  model,
  systemPrompt,
  userPrompt,
  apiKey,
  reasoningEffort,
  maxOutputTokens,
}: StreamCompletionParams): AsyncGenerator<string, void, void> {
  // Use Azure only when configured AND the caller did not supply their own key
  // (a user-supplied key always implies vanilla OpenAI).
  const azure = apiKey?.trim() ? null : getAzureConfig();

  if (azure) {
    // ------------------------------------------------------------------
    // Azure OpenAI — Chat Completions API
    // ------------------------------------------------------------------
    const client = new AzureOpenAI({
      apiKey: azure.apiKey,
      endpoint: azure.endpoint,
      deployment: azure.deployment,
      apiVersion: azure.apiVersion,
    });

    // Use `stream: true as const` so TypeScript narrows the return type to
    // Stream<ChatCompletionChunk> instead of the union type.
    const stream = await client.chat.completions.create({
      model: azure.deployment,
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userPrompt },
      ],
      stream: true as const,
      ...(maxOutputTokens ? { max_tokens: maxOutputTokens } : {}),
      ...(reasoningEffort && isReasoningModel(azure.deployment)
        ? { reasoning_effort: reasoningEffort }
        : {}),
    });

    for await (const chunk of stream) {
      const delta = chunk.choices[0]?.delta?.content;
      if (delta) yield delta;
    }
    return;
  }

  // ------------------------------------------------------------------
  // Vanilla OpenAI — Responses API (backup)
  // ------------------------------------------------------------------
  const client = new OpenAI({ apiKey: resolveApiKey(apiKey) });

  const stream = await client.responses.create({
    model,
    stream: true,
    input: [
      { role: "system", content: systemPrompt },
      { role: "user", content: userPrompt },
    ],
    ...(reasoningEffort ? { reasoning: { effort: reasoningEffort } } : {}),
    ...(maxOutputTokens ? { max_output_tokens: maxOutputTokens } : {}),
  });

  for await (const event of stream) {
    if (event.type === "response.output_text.delta") {
      if (event.delta) {
        yield event.delta;
      }
      continue;
    }

    if (event.type === "error") {
      const message = event.message ?? "OpenAI stream failed.";
      throw new Error(message);
    }
  }
}

// ---------------------------------------------------------------------------
// Token counting
// ---------------------------------------------------------------------------

interface CountInputTokensParams {
  model: string;
  systemPrompt: string;
  userPrompt: string;
  apiKey?: string;
  reasoningEffort?: ReasoningEffort;
}

export async function countInputTokens({
  model,
  systemPrompt,
  userPrompt,
  apiKey,
  reasoningEffort,
}: CountInputTokensParams): Promise<number> {
  const azure = apiKey?.trim() ? null : getAzureConfig();
  if (azure) {
    // Azure Chat Completions has no dedicated token-count endpoint;
    // fall back to the length heuristic.
    return estimateTokens(systemPrompt + userPrompt);
  }

  // Vanilla OpenAI — Responses input-tokens API (backup)
  const client = new OpenAI({ apiKey: resolveApiKey(apiKey) });

  const response = await client.responses.inputTokens.count({
    model,
    input: [
      { role: "system", content: systemPrompt },
      { role: "user", content: userPrompt },
    ],
    ...(reasoningEffort ? { reasoning: { effort: reasoningEffort } } : {}),
  });

  return response.input_tokens;
}
