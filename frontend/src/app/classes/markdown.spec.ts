import { prepareMarkdown, renderMarkdown } from './markdown';

describe('markdown rendering of artifacts', () => {
  // Shape of the LLM conversations in the artifacts: newlines stored as a literal "\n"
  const conversation = 'USER: what does len() do and mean in python ||| ASSISTANT: Great question! 🌟\\n\\n' +
    '### ✅ `len()` in Python means **"length"**\\n\\n---\\n\\n' +
    '#### 1. **Strings**\\n```python\\ntext = "Hello"\\nprint(len(text)) # Output: 5\\n```\\n\\n' +
    '| Object | `len()` Result |\\n|----------------|----------------|\\n| `"cat"` | 3 |\\n| `["a", "b"]` | 2 |';

  function toElement(html: string): HTMLElement {
    const div = document.createElement('div');
    div.innerHTML = html;
    return div;
  }

  it('renders an escaped LLM conversation', () => {
    const element = toElement(renderMarkdown(conversation));

    expect(element.querySelector('h3')?.textContent).toContain('len() in Python means');
    expect(element.querySelector('h4')?.textContent).toContain('1. Strings');
    expect(element.querySelector('pre code')?.textContent).toContain('print(len(text)) # Output: 5');
    expect(element.querySelectorAll('table tbody tr').length).toBe(2);
    // Turn separator and speaker labels
    expect(element.querySelectorAll('hr').length).toBe(2);
    const speakers = Array.from(element.querySelectorAll('strong')).map(e => e.textContent);
    expect(speakers).toContain('USER:');
    expect(speakers).toContain('ASSISTANT:');
  });

  it('only unescapes newlines when the text has no real newlines', () => {
    expect(prepareMarkdown('a\\nb')).toBe('a\nb');
    // Text with real newlines is left alone, e.g. "\n" inside code
    expect(prepareMarkdown('print("a\\nb")\nnext line')).toBe('print("a\\nb")\nnext line');
  });

  it('removes scripts, event handlers and images', () => {
    const html = renderMarkdown('hi <script>alert(1)</script> <a href="javascript:alert(1)">x</a> ' +
      '<b onclick="alert(1)">b</b> ![img](https://example.org/a.png) <img src=x onerror="alert(1)">');
    const element = toElement(html);

    expect(element.querySelector('script')).toBeNull();
    expect(element.querySelector('img')).toBeNull();
    expect(element.querySelector('[onclick]')).toBeNull();
    expect(element.querySelector('[onerror]')).toBeNull();
    expect(html).not.toContain('javascript:');
  });

  it('opens links in a new tab', () => {
    const link = toElement(renderMarkdown('[docs](https://docs.python.org)')).querySelector('a');
    expect(link?.getAttribute('target')).toBe('_blank');
    expect(link?.getAttribute('rel')).toContain('noopener');
  });

  it('handles empty input', () => {
    expect(renderMarkdown('')).toBe('');
    expect(renderMarkdown(undefined)).toBe('');
  });
});
