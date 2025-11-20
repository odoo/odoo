import { _t } from '@web/core/l10n/translation';

/**
 * Update the quick reorder side panel.
 *
 * @param {Object} data
 * @return {void}
 */
function updateQuickReorderSidebar(data) {
    const quickReorderButton  = document.getElementById('quick_reorder_button');
    document.querySelectorAll('.o_wsale_quick_reorder_line_group').forEach(el => el.remove());
    if (data['website_sale.quick_reorder_history'].trim()) {
        document.querySelector('#quick_reorder_sidebar .offcanvas-body').insertAdjacentHTML(
            'afterbegin', data['website_sale.quick_reorder_history']
        );
        quickReorderButton.removeAttribute('disabled');
        quickReorderButton.parentElement.title = "";
    } else {
        quickReorderButton.click();
        quickReorderButton.setAttribute('disabled', 'true');
        quickReorderButton.parentElement.title = _t("No previous products available for reorder.");
    }
}

/**
 * Displays `message` in an alert box at the top of the page if it's a
 * non-empty string.
 *
 * @param {string | null} message
 */
function showWarning(message) {
    if (!message) return;
    document.querySelector('.oe_website_sale')?.querySelector('#data_warning')?.remove();

    const alertDiv = document.createElement('div');
    alertDiv.classList.add('alert', 'alert-danger', 'alert-dismissible');
    alertDiv.role = 'alert';
    alertDiv.id = 'data_warning';
    const closeButton = document.createElement('button');
    closeButton.classList.add('btn-close');
    closeButton.type = 'button'; // Avoid default submit type in case of a form.
    closeButton.dataset.bsDismiss = 'alert';
    const messageSpan = document.createElement('span');
    messageSpan.textContent = message;
    alertDiv.appendChild(closeButton);
    alertDiv.appendChild(messageSpan);
    document.querySelector('.oe_website_sale').prepend(alertDiv);
}

/**
 * Return the selected attribute values from the given container.
 *
 * @param {Element} container the container to look into
 */
function getSelectedAttributeValues(container) {
    return Array.from(container.querySelectorAll(
        'input.js_variant_change:checked, select.js_variant_change'
    )).map(el => parseInt(el.value));
}

export default {
    showWarning: showWarning,
    getSelectedAttributeValues: getSelectedAttributeValues,
    updateQuickReorderSidebar: updateQuickReorderSidebar,
};
