import { patch } from "@web/core/utils/patch";
import { AvatarCard } from "@mail/core/web/avatar_card/avatar_card";
import { HtmlViewer } from "@html_editor/components/html_viewer/html_viewer";

patch(HtmlViewer.prototype, {
    retargetLinks(container) {
        for (const linkEl of container.querySelectorAll("a.o_mail_redirect")) {
            this.addDomListener(linkEl, "click", (ev) => {
                this.env.services.popover.add(ev.target, AvatarCard, {
                    id: linkEl.dataset.oeId,
                    model: linkEl.dataset.oeModel,
                });
                ev.preventDefault();
            });
        }
        super.retargetLinks(container);
    },
});
