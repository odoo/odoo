import { describe, expect, test } from "@odoo/hoot";
import { serializeChanges } from "@web_tour/tour_service/tour_utils";
import { queryOne } from "@odoo/hoot-dom";
import { Component, xml } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

class Root extends Component {
    static template = xml`<div id="mytemplate">
    <div>coucou</div>    
            <div class="arsenal">Arsenal</div>    
            <div class="liverpool">Liverpool</div>    
            <div><div>blabla</div></div>    
            <div class="mancity">
            <section id="players">
            <div class="doku">Jeremy</div><div class="kdb">Kevin</div>   
            </section>
            </div>
            <div><div>blabla</div></div>    
            <div class="dortmund">
            <section id="players">
            <div class="haland">Erling</div><div class="konate">Ngolo</div>
            <div class="reus">Marco<span>etoile</span></div>   
            </section>
            </div> 
            <div>coucou</div>   
            <div>coucou</div>
    
    </div>`;
    static props = ["*"];
}

test("add/remove nodes", async () => {
    await mountWithCleanup(Root);
    const snapshot = queryOne("#mytemplate").cloneNode(true);
    const myBeautifulNode = document.createElement("a");
    myBeautifulNode.setAttribute("href", "https://www.mybeautiful.node");
    myBeautifulNode.textContent = "coucou";
    queryOne("#mytemplate div.doku").appendChild(myBeautifulNode);
    queryOne(".mancity #players").removeChild(queryOne("div.kdb"));
    queryOne(".dortmund #players").removeChild(queryOne("div.konate"));
    queryOne(".dortmund #players").removeChild(queryOne("div.haland"));
    const changes = serializeChanges(snapshot, queryOne("#mytemplate"));
    expect(changes).toEqual([
        "div#mytemplate section#players : The node {div.kdb} has been removed.",
        'div#mytemplate div.doku : The node {a[href="https://www.mybeautiful.node"]} has been added.',
        "div#mytemplate section#players : The node {div.haland} has been removed.",
        "div#mytemplate section#players : The node {div.konate} has been removed.",
        "div#mytemplate div.reus : Attribute class has changed : haland => reus",
        "div#mytemplate div.reus : The node {span} has been added.",
        "div#mytemplate div.reus : Text has changed : Erling => Marco",
    ]);
});

test("change text content", async () => {
    await mountWithCleanup(Root);
    const snapshot = queryOne("#mytemplate").cloneNode(true);
    queryOne(".doku").textContent = "blibli";
    queryOne(".kdb").textContent = "bloblo";
    const changes = serializeChanges(snapshot, queryOne("#mytemplate"));
    expect(changes).toEqual([
        "div#mytemplate div.doku : Text has changed : Jeremy => blibli",
        "div#mytemplate div.kdb : Text has changed : Kevin => bloblo",
    ]);
});
