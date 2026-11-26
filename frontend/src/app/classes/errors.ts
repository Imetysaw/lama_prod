/**
 * Returns the error message the backend sent with a failed request (e.g. "A label type with
 * this name already exists"), or the fallback when there is none.
 */
export function serverErrorMessage(error: any, fallback: string): string {
  const data = error?.response?.data;
  if (typeof data === 'string' && data.length > 0 && data.length < 300 && !data.trimStart().startsWith('<')) {
    return data;
  }
  return fallback;
}
