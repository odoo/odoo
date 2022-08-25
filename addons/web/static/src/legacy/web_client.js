odoo.define("web.web_client", function () {
    return {};
});

odoo.define("web.pseudo_web_client", function (require) {
    const FakeWebClient = require("web.web_client");

    function makeLegacyWebClientService(legacyEnv) {
        const legacyPseudoWebClient = {
            dependencies: ["title", "router"],
            start(env) {
                function setTitlePart(part, title = null) {
                    env.services.title.setParts({ [part]: title });
                }
                legacyEnv.bus.on("set_title_part", null, (params) => {
                    const { part, title } = params;
                    setTitlePart(part, title || null);
                });
                Object.assign(FakeWebClient, {
                    do_push_state(state) {
                        if ("title" in state) {
                            setTitlePart("action", state.title);
                            delete state.title;
                        }
                        env.services.router.pushState(state);
                    },
                    set_title(title) {
                        setTitlePart("action", title);
                    },
                });
            },
        };
        return legacyPseudoWebClient;
    }

    return makeLegacyWebClientService;
});
