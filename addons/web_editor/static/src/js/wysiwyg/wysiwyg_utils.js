/** @odoo-module **/

export function isImg(node) {
    return (node && (node.nodeName === "IMG" || (node.className && node.className.match(/(^|\s)(media_iframe_video|o_image|fa)(\s|$)/i))));
}

function getIntermediateNodes(rootNode) {
    const nodes = [];
    for (const node of rootNode.childNodes) {
        nodes.push(node);
        nodes.push(...getIntermediateNodes(node));
    }
    return nodes;
}

export function encodeNodeToText(rootNode) {
    const fake = document.createElement('fake');
    for (const node of [...rootNode.cloneNode(true).childNodes]) {
        fake.appendChild(node);
    }

    const nodes = getIntermediateNodes(fake);

    const images = [];
    for (const node of nodes) {
        if (isImg(node)) {
            node.before(document.createTextNode('[IMG]'));
            node.remove();
            images.push(node);
        }
    }

    const text = fake.innerText.replace(/[ \t\r\n]+/g, ' ');
    return [text, images];
}

export function decodeText(text, images = []) {
    text = _.escape(text);
    for (const img of images) {
        text = text.replace(/\[IMG\]/, img.outerHTML);
    }
    return text;
}
