const DEFAULT_MODEL = "gpt-5.2";

function readEnvValue(name: string): string | undefined {
  const value = process.env[name]?.trim();
  return value ? value : undefined;
}

/**
 * Returns the effective model identifier to use for API calls AND display:
 * - Azure OpenAI: returns the deployment name (AZURE_OPENAI_DEPLOYMENT)
 * - Vanilla OpenAI: returns OPENAI_MODEL or the hardcoded default
 *
 * Azure is considered active when all three required env vars are present
 * (AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT).
 */
export function getModel(): string {
  const azureKey = readEnvValue("AZURE_OPENAI_API_KEY");
  const azureEndpoint = readEnvValue("AZURE_OPENAI_ENDPOINT");
  const azureDeployment = readEnvValue("AZURE_OPENAI_DEPLOYMENT");
  if (azureKey && azureEndpoint && azureDeployment) {
    return azureDeployment;
  }
  return readEnvValue("OPENAI_MODEL") ?? DEFAULT_MODEL;
}
