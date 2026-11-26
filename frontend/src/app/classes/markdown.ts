import { marked } from 'marked';
import DOMPurify from 'dompurify';

/*
 * Renders artifact text (typically LLM conversations) as markdown.
 * The output is sanitized with DOMPurify, so artifact text can never inject scripts.
 */

// Tags that are removed from the rendered markdown. Images are removed so that viewing an
// artifact never makes the browser contact a third-party server; forms are never needed.
const FORBIDDEN_TAGS = ['img', 'style', 'form', 'input', 'button', 'textarea', 'select', 'iframe'];

// Links in artifacts open in a new tab and do not get access to LaMa (window.opener)
DOMPurify.addHook('afterSanitizeAttributes', (node: Element) => {
  if (node.tagName === 'A' && node.hasAttribute('href')) {
    node.setAttribute('target', '_blank');
    node.setAttribute('rel', 'noopener noreferrer nofollow');
  }
});

/**
 * Prepares artifact text for markdown rendering:
 * - Text that was exported with escaped newlines (a literal backslash followed by "n") and
 *   that contains no real newlines gets real newlines, so headings, lists and code blocks work.
 * - Conversation turns separated by "|||" are shown with a horizontal line in between,
 *   and a speaker prefix such as "USER:" or "ASSISTANT:" at the start of a turn is shown in bold.
 */
export function prepareMarkdown(text: string): string {
  let result = text;
  if (!/[\r\n]/.test(result) && /\\n/.test(result)) {
    result = result.replace(/\\r\\n|\\n|\\r/g, '\n').replace(/\\t/g, '\t');
  }
  return result
    .split('|||')
    .map(turn => turn.trim().replace(/^(USER|ASSISTANT|SYSTEM|HUMAN|AI|BOT)\s*:\s*/i, '**$1:** '))
    .join('\n\n---\n\n');
}

/**
 * Converts artifact text to sanitized HTML
 * @param text the raw artifact text
 * @returns HTML that is safe to insert into the page
 */
export function renderMarkdown(text: string | undefined | null): string {
  if (!text) return '';
  const html = marked.parse(prepareMarkdown(text), {
    gfm: true,
    // LLM output uses single newlines as line breaks
    breaks: true,
    headerIds: false,
    mangle: false,
  });
  return DOMPurify.sanitize(html, { FORBID_TAGS: FORBIDDEN_TAGS, FORBID_ATTR: ['style'] });
}
