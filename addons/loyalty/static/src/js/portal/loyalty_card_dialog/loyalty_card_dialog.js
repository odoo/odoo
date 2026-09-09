import { Component, t, useProps } from '@odoo/owl';
import { Dialog } from '@web/core/dialog/dialog';

export class PortalLoyaltyCardDialog extends Component {
    static components = { Dialog };
    static template = 'loyalty.portal_loyalty_card_dialog';
    props = useProps({
        close: t.function(),
        img_path: t.string(),
        program: t.object({
            program_name: t.string(),
        }),
        card: t.object({
            points_display: t.any(),
            expiration_date: t.any().optional(),
            id: t.any(),
        }),
        history_lines: t.array(
            t.object({
                order_id: t.any().optional(),
                order_portal_url: t.any().optional(),
                description: t.any(),
                points: t.any(),
            })
        ),
    });

    setup() {
        this.csrf_token = odoo.csrf_token;
    }
}
