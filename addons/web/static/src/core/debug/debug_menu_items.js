/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { routeToUrl } from "@web/core/browser/router_service";
import { registry } from "@web/core/registry";
import { Component, xml } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

function activateAssetsDebugging({ env }) {
    return {
        type: "item",
        description: env._t("Activate Assets Debugging"),
        callback: () => {
            browser.location.search = "?debug=assets";
        },
        sequence: 410,
    };
}

function activateTestsAssetsDebugging({ env }) {
    return {
        type: "item",
        description: env._t("Activate Tests Assets Debugging"),
        callback: () => {
            browser.location.search = "?debug=assets,tests";
        },
        sequence: 420,
    };
}

export function regenerateAssets({ env }) {
    return {
        type: "item",
        description: env._t("Regenerate Assets Bundles"),
        callback: async () => {
            const domain = [
                "&",
                ["res_model", "=", "ir.ui.view"],
                "|",
                ["name", "=like", "%.assets_%.css"],
                ["name", "=like", "%.assets_%.js"],
            ];
            const ids = await env.services.orm.search("ir.attachment", domain);
            await env.services.orm.unlink("ir.attachment", ids);
            browser.location.reload();
        },
        sequence: 430,
    };
}

// Dialog Declaration
// it's used to display all the assets used in a page and their size
class ViewAssetsDialog extends Component {}
ViewAssetsDialog.template = xml`
<Dialog title="this.constructor.title">
    <p>
    Found files :
    </p>
    <pre t-esc="props.output"/>
</Dialog>`;
ViewAssetsDialog.components = { Dialog };
ViewAssetsDialog.props = {
    output: { type: String },
    close: { type: Function },
};
ViewAssetsDialog.title = "Assets size";

async function getUsedBundles() {
    const url = "./";
    const regex = /(?<=\=\"\/web\/assets\/)(.*)(?=\" data-asset-bundle)/gm;

    const page = await fetch(url)
        .then( r => r.text() )
        .then( t => {return(t);});

    const matches = page.match(regex); // get all bundles declared in 'page'
    let bundles = [];
    matches.forEach((match) => {
        let parts = match.split('/');
        bundles.push({path : match, name : parts[parts.length - 1]});
    });
    return bundles;
}

function getStats(bundle) {
    const regex = /\/\* | \*\//;
    let parts = bundle.split(regex);
    parts.splice(0,1);
    let parts_info = [];
    for (let i = 0; i < parts.length; i+=2){
        let data = parts[i + 1];
        parts_info.push({
            'file': parts[i],
            'data': data,
            'length': data.length,
        });
    }
    return parts_info.sort(function(a, b){return a.length - b.length;}).reverse();
}

export function viewAssetsSize({ env }) {
    return {
        type: "item",
        description: env._t("View Assets Size"),
        callback: async() => {
            const bundles= await getUsedBundles();
            let output="";
            for (let bundle in bundles){
                const url = "./web/assets/"+bundles[bundle].path;
                const bundle_content = await fetch(url)
                    .then( r => r.text() )
                    .then( t => {return(t);});
                const stats = getStats(bundle_content);

                output+="Assets in " + bundles[bundle].name + " :\n";
                for (let stat in stats ){
                    output += stats[stat].file + " : " + stats[stat].length + " o\n";
                }
                output+='\n';
            }

            env.services.dialog.add(ViewAssetsDialog, { output } );
        },
        sequence: 450,
    };
}

function becomeSuperuser({ env }) {
    const becomeSuperuserURL = browser.location.origin + "/web/become";
    return {
        type: "item",
        description: env._t("Become Superuser"),
        hide: !env.services.user.isAdmin,
        href: becomeSuperuserURL,
        callback: () => {
            browser.open(becomeSuperuserURL, "_self");
        },
        sequence: 440,
    };
}

function leaveDebugMode({ env }) {
    return {
        type: "item",
        description: env._t("Leave the Developer Tools"),
        callback: () => {
            const route = env.services.router.current;
            route.search.debug = "";
            browser.location.href = browser.location.origin + routeToUrl(route);
        },
        sequence: 460,
    };
}

registry
    .category("debug")
    .category("default")
    .add("activateAssetsDebugging", activateAssetsDebugging)
    .add("regenerateAssets", regenerateAssets)
    .add("becomeSuperuser", becomeSuperuser)
    .add("leaveDebugMode", leaveDebugMode)
    .add("activateTestsAssetsDebugging", activateTestsAssetsDebugging)
    .add("viewAssetSize", viewAssetsSize);
