import { Pipe, PipeTransform } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { renderMarkdown } from 'app/classes/markdown';

/**
 * Renders artifact text as sanitized markdown HTML: <div [innerHTML]="text | markdown"></div>
 * The pipe is pure, so the text is only rendered again when it changes.
 */
@Pipe({ name: 'markdown' })
export class MarkdownPipe implements PipeTransform {
  constructor(private sanitizer: DomSanitizer) { }

  transform(text: string | undefined | null): SafeHtml {
    // renderMarkdown already sanitizes the HTML with DOMPurify. Angular's own sanitizer
    // would additionally strip harmless markup (and log warnings), so it is bypassed here.
    return this.sanitizer.bypassSecurityTrustHtml(renderMarkdown(text));
  }
}
