import { useAutoresize } from "@web/core/utils/autoresize";

/**
 * This overriden version of the resizeTextArea method is specificly done for the product_label_section_and_note widget
 * His necessity is found in the fact that the cell of said widget doesn't contain only the input or textarea to resize
 * but also another node containing the name of the product if said data is available. This means that the autoresize
 * method which sets the height of the parent cell should sometimes add an additional row to the parent cell so that
 * no text overflows
 *
 * @param {Ref} ref
 */
export function useProductAndLabelAutoresize(ref, options = {}) {
    useAutoresize(ref, { 
        onMounted: productAndLabelResizeTextArea, 
        onResize: productAndLabelResizeTextArea,
        ...options,
    });
}


const pendingHeightUpdates = new Map(); // element → height string
let flushScheduled = false;

function flushHeightUpdates() {
  for (const [el, height] of pendingHeightUpdates) {
    el.style.height = height;
  }
  pendingHeightUpdates.clear();
  flushScheduled = false;
}

export function productAndLabelResizeTextArea(textarea, options = {}) {
  const style = window.getComputedStyle(textarea);
  if (options.targetParentName) {
    let target = textarea.parentElement;
    let shouldContinue = true;
    while (target && shouldContinue) {
      const totalParentHeight = Array.from(target.children).reduce((total, child) => {
        const childHeight = child.style.height || style.lineHeight;
        return total + parseFloat(childHeight);
      }, 0);

      pendingHeightUpdates.set(target, `${totalParentHeight}px`); // deferred

      if (target.getAttribute("name") === options.targetParentName) {
        shouldContinue = false;
      }
      target = target.parentElement;
    }

    if (!flushScheduled) {
      flushScheduled = true;
      queueMicrotask(flushHeightUpdates);
    }
  }
}