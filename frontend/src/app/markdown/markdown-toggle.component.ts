import { Component, OnDestroy } from '@angular/core';
import { Subscription } from 'rxjs';
import { MarkdownPreferenceService } from './markdown-preference.service';

/**
 * Switch to show artifact text formatted as markdown or as raw text
 */
@Component({
  selector: 'app-markdown-toggle',
  template: `
    <div class="form-check form-switch markdown-toggle"
      ngbTooltip="Show the artifact text formatted (headings, lists, code, tables) or as raw text">
      <input class="form-check-input" type="checkbox" role="switch" id="{{ id }}"
        [checked]="enabled" (change)="toggle($any($event.target).checked)">
      <label class="form-check-label" for="{{ id }}">Format markdown</label>
    </div>`,
  styles: [`
    .markdown-toggle { display: inline-block; margin: 0; white-space: nowrap; }
    .form-check-input:checked { background-color: #38474e; border-color: #38474e; }
    .form-check-input:focus { box-shadow: none; }
  `]
})
export class MarkdownToggleComponent implements OnDestroy {
  private static counter = 0;
  // Unique id, in case a page shows more than one toggle
  id = `markdownToggle-${MarkdownToggleComponent.counter++}`;
  enabled = true;
  private subscription: Subscription;

  constructor(private preference: MarkdownPreferenceService) {
    this.subscription = this.preference.enabled.subscribe(value => this.enabled = value);
  }

  toggle(enabled: boolean): void {
    this.preference.set(enabled);
  }

  ngOnDestroy(): void {
    this.subscription.unsubscribe();
  }
}
