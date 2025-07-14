import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BuilderAction } from "@html_builder/core/builder_action";
class AvatarCountAction extends BuilderAction {
    static id = "avatarCount";

    getValue({ editingElement, params: { mainParam: action } = {} }) {
        if (action === 'countValue') {
            return editingElement.dataset.countValue || '10+';
        }
        if (action === 'showCount') {
            return editingElement.classList.contains('o_show_count');
        }
        return null;
    }

    isApplied({ editingElement, params: { mainParam: action } = {} }) {
        if (action === 'showCount') {
            const countElement = editingElement.querySelector('.o_avatar_count');
            return countElement && !countElement.classList.contains('d-none');
        }
        return false;
    }

    apply({ editingElement, params: { mainParam: action } = {}, value }) {
        if (action === 'showCount') {
            const countElement = this._ensureCountElement(editingElement);
            if (countElement) {
                countElement.classList.toggle('d-none');
                countElement.classList.toggle('d-flex');
                this._copyStyling(editingElement);
            }
        } else if (action === 'countValue') {
            editingElement.dataset.countValue = value || '10+';
            const countElement = editingElement.querySelector('.o_avatar_count');
            if (countElement) {
                countElement.textContent = value || '10+';
            }
        } else if (action === 'copyStyling') {
            this._copyStyling(editingElement);
        }
    }

    _ensureCountElement(editingElement) {
        let countElement = editingElement.querySelector('.o_avatar_count');
        if (!countElement) {
            const wrapper = editingElement.querySelector('.s_customers_avatars_wrapper');
            if (wrapper) {
                countElement = document.createElement('div');
                countElement.className = 'o_avatar_count d-none';
                countElement.textContent = editingElement.dataset.countValue || '10+';
                wrapper.appendChild(countElement);
            }
        }
        return countElement;
    }

    _copyStyling(editingElement) {
        const countElement = editingElement.querySelector('.o_avatar_count');
        const firstAvatar = editingElement.querySelector('.o_avatar');

        if (countElement && firstAvatar) {
            const isHidden = countElement.classList.contains('d-none');
            const isVisible = countElement.classList.contains('d-flex');

            countElement.className = 'o_avatar_count';

            if (isHidden) countElement.classList.add('d-none');
            if (isVisible) countElement.classList.add('d-flex');

            const classesToCopy = Array.from(firstAvatar.classList).filter(cls =>
                cls !== 'img' && cls !== 'o_avatar'
            );
            countElement.classList.add(...classesToCopy);
            countElement.style.cssText = firstAvatar.style.cssText;
        }
    }
}

class CustomersAvatarsOptionPlugin extends Plugin {
    static id = "customersAvatarOption";
    selector = ".s_customers_avatars";
    resources = {
        builder_options: [
            {
                template: "website.CustomersAvatarsOption",
                selector: this.selector,
            },
        ],
        builder_actions: {
            avatarCount: AvatarCountAction,
        },
        so_content_addition_selector: [".s_customers_avatars"],
    };
}

registry.category("website-plugins").add(CustomersAvatarsOptionPlugin.id, CustomersAvatarsOptionPlugin);
