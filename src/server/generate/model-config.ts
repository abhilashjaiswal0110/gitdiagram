const DEFAULT_MODEL = "gpt-5.2";

function readEnvValue(name: string): string | undefined {
  const value = process.env[name]?.trim();
  return value ? value : undefined;
}

/**
 * Returns the effective model identifier to use for API calls AND display.
 *
 * - When `overrideApiKey` is provided the caller is using their own vanilla
 *   OpenAI key, so we always return the vanilla OpenAI model name.
 * - Otherwise Azure is used when all three AZURE_OPENAI_* vars are set;
 *   the Azure deployment name is returned.
 * - Falls back to OPENAI_MODEL / the hardcoded default.
 *
 * @param overrideApiKey - Optional user-supplied API key (request-level).
 */
export function getModel(overrideApiKey?: string): string {
  // A user-supplied key means vanilla OpenAI regardless of Azure configuration
  if (!overrideApiKey?.trim()) {
    const azureKey = readEnvValue("AZURE_OPENAI_API_KEY");
    const azureEndpoint = readEnvValue("AZURE_OPENAI_ENDPOINT");
    const azureDeployment = readEnvValue("AZURE_OPENAI_DEPLOYMENT");
    if (azureKey && azureEndpoint && azureDeployment) {
      return azureDeployment;
    }
  }
  return readEnvValue("OPENAI_MODEL") ?? DEFAULT_MODEL;
}
