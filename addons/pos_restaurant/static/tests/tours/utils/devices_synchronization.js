/* global posmodel */

export function notify() {
    return {
        trigger: "body",
        run: async () => {
            try {
                const orm = posmodel.env.services.orm;
                await orm.call("pos.config", "notify_synchronisation", [
                    odoo.pos_config_id,
                    odoo.pos_session_id,
                    0,
                ]);
            } catch (error) {
                console.log(error);
            }
        },
    };
}
