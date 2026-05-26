import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

registry.category("website.team_board.contact_methods").add("send_message", {
    label: _t("Send a message"),
    sequence: 10,
    className: "btn-primary",
    async handler({ cardEl, button, services, waitFor, closeModal }) {
        button.setLoading(_t("Sending..."));
        // Placeholder demo: every third card fails the simulated send so
        // both the success and failure UIs can be exercised without a
        // backend round-trip.
        const cards = Array.from(cardEl.closest(".s_team_board").querySelectorAll(".s_card"));
        const shouldFail = cards.indexOf(cardEl) % 3 === 2;
        try {
            await waitFor(
                new Promise((resolve, reject) => {
                    setTimeout(
                        () => (shouldFail ? reject(new Error("simulated")) : resolve()),
                        1000
                    );
                })
            );
            closeModal();
            services.notification.add(_t("Your message has been sent."), { type: "success" });
        } catch {
            button.reset();
            services.notification.add(_t("Could not send your message."), { type: "danger" });
        }
    },
});
