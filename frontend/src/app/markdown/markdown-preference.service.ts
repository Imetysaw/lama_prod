import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

const STORAGE_KEY = 'lama_render_markdown';

/**
 * Remembers whether artifact text is shown formatted (markdown) or as raw text.
 * The choice is shared by all pages and stored in the browser.
 */
@Injectable({
  providedIn: 'root'
})
export class MarkdownPreferenceService {
  readonly enabled = new BehaviorSubject<boolean>(MarkdownPreferenceService.load());

  private static load(): boolean {
    try {
      return localStorage.getItem(STORAGE_KEY) !== 'false';
    } catch {
      return true;
    }
  }

  set(enabled: boolean): void {
    try {
      localStorage.setItem(STORAGE_KEY, String(enabled));
    } catch {
      // Storage unavailable (e.g. private mode): the choice only lasts for this page
    }
    this.enabled.next(enabled);
  }
}
