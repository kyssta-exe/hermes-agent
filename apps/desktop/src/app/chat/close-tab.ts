import { closeWorkspaceTab } from '@/components/pane-shell/tree/store'
import { isFocusWithin } from '@/lib/keybinds/combo'
import { $filePreviewTarget, $previewTarget, closeActiveRightRailTab } from '@/store/preview'

/**
 * ⌘W — close the tab of the context you're in, by precedence:
 *   1. a focused terminal → pass through; Ctrl+W is a readline
 *      delete-word-back command inside a terminal, not a close-tab shortcut,
 *   2. an open preview → its active preview tab (unchanged from pre-tiling),
 *   3. the MAIN zone → its active tab (a session tile stacked into the workspace).
 * Returns false when nothing closes, so ⌘W is a no-op — it never closes the
 * window (a bare workspace stays put). Shared by the keyboard path (Win/Linux)
 * and the macOS menu-accelerator IPC.
 */
export function closeActiveTab(): boolean {
  if (isFocusWithin('[data-terminal]')) {
    // Terminal focused: Ctrl+W/Cmd+W is a readline word-delete command,
    // not a close-tab shortcut. Let it pass through so the shell sees it.
    // The terminal tab can be closed via the close button, context menu,
    // or by clicking elsewhere first.
    return false
  }

  if ($filePreviewTarget.get() || $previewTarget.get()) {
    closeActiveRightRailTab()

    return true
  }

  return closeWorkspaceTab()
}
