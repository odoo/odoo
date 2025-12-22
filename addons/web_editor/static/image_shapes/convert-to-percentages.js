// The goal of this script is to have a shape ready for use with the
// "Shape on Image" feature of Odoo.
// Therefor we need to rearrange the file a little.
// Marks which axis each parameter of a command belongs to, as well as whether
// It's a positional measurement (x/y), a distance (dx/dy) or none (angles, flags)
const commandAxes = {
    'M': ['x', 'y'],
    'm': ['dx', 'dy'],
    'L': ['x', 'y'],
    'l': ['dx', 'dy'],
    'H': ['x'],
    'h': ['dx'],
    'V': ['y'],
    'v': ['dy'],
    'Z': [],
    'z': [],
    'C': ['x', 'y', 'x', 'y', 'x', 'y'],
    'c': ['dx', 'dy', 'dx', 'dy', 'dx', 'dy'],
    'S': ['x', 'y', 'x', 'y'],
    's': ['dx', 'dy', 'dx', 'dy'],
    'Q': ['x', 'y', 'x', 'y'],
    'q': ['dx', 'dy', 'dx', 'dy'],
    'T': ['x', 'y'],
    't': ['dx', 'dy'],
    'A': ['dx', 'dy', 'none', 'none', 'none', 'x', 'y'],
    'a': ['dx', 'dy', 'none', 'none', 'none', 'dx', 'dy'],
};

const toUserSpace = (x, y, width, height, precision = 4) => ({
    x: val => +((parseFloat(val) - x) / width).toFixed(precision),
    dx: val => +(parseFloat(val) / width).toFixed(precision),
    y: val => +((parseFloat(val) - y) / height).toFixed(precision),
    dy: val => +(parseFloat(val) / height).toFixed(precision),
    none: val => val,
});

const filePicker = document.getElementById('svgPicker');
const submitButton = document.getElementById('submitButton');
submitButton.addEventListener('click', async (ev) => {
    if (!filePicker.files.length > 0) {
        alert('Please select files using the file picker first');
        return;
    }
    Array.from(filePicker.files).forEach(async file => {
        const fileReader = new FileReader();
        const readerPromise = new Promise((resolve, reject) => {
            fileReader.addEventListener('load', () => resolve(fileReader.result));
            fileReader.addEventListener('error', () => reject(fileReader.error));
        });
        fileReader.readAsText(file, 'utf-8');
        const svgString = await readerPromise;
        const parser = new DOMParser();
        const svg = parser.parseFromString(svgString, 'image/svg+xml');
        const path = svg.getElementById('filterPath');
        const svgDocumentElement = svg.documentElement;
        // Some SVGs come without xlink
        svgDocumentElement.setAttribute('xmlns:xlink', 'http://www.w3.org/1999/xlink');
        // We add the SVG to the body so we can take measurements of its
        // original size
        document.body.appendChild(svg.documentElement);
        const { x, y, width, height } = svgDocumentElement.getBBox();
        const scalers = toUserSpace(x, y, width, height);

        // Converts the clipPath in values between 0 and 1 so we can use
        // object bounding box as clip path units. It will make the clip path
        // always adapt to the size of the picture.
        const commands = path.getAttribute('d').match(/[a-z][^a-z]*/ig).map(c => {
            return c.split(/[, ]|(?=-)|(?<=[a-z])(?=[0-9])/i).filter(part => !!part.length);
        });
        const relSpaceCommands = commands.map(([command, ...nums]) => {
            const axes = commandAxes[command];
            const relSpaceNums = nums.map((n, i) => {
                const scaler = scalers[axes[i % axes.length]];
                return scaler(n);
            });
            return `${command}${relSpaceNums.join(',')}`.replace(/,-/g, '-');
        });
        path.setAttribute('d', relSpaceCommands.join(''));
        path.removeAttribute('fill');
        svgDocumentElement.removeAttribute('viewBox');

        let defsEl = svgDocumentElement.querySelector('defs');
        if (!defsEl) {
            defsEl = svg.createElementNS('http://www.w3.org/2000/svg', 'defs');
            svgDocumentElement.appendChild(defsEl);
        }

        let clipPathEl = svgDocumentElement.querySelector('clipPath');
        if (!clipPathEl) {
            clipPathEl = svg.createElementNS('http://www.w3.org/2000/svg', 'clipPath');
            clipPathEl.setAttribute('id', 'clip-path');
            defsEl.appendChild(clipPathEl);
        }

        clipPathEl.setAttribute('clipPathUnits', 'objectBoundingBox');
        const backgroundEls = svgDocumentElement.getElementsByClassName('background');
        // We set the BG elements into their own svg so that when the total
        // space gets stretched out, so does the backgrounds elements
        Array.from(backgroundEls).forEach(el => {
            const bgBbox = el.getBBox();
            const svgBackground = document.createElement('svg');
            const strokeWidth = el.getAttribute('stroke-width');
            // If the background has a strokeWidth, the viewBox need to take it
            // into account
            if (strokeWidth) {
                const adj = parseFloat(strokeWidth) / 2;
                svgBackground.setAttributeNS('http://www.w3.org/2000/svg', 'viewBox',
                `${bgBbox.x - adj} ${bgBbox.y - adj} ${bgBbox.width + (adj * 2)} ${bgBbox.height + (adj * 2)}`);
            } else {
                svgBackground.setAttributeNS('http://www.w3.org/2000/svg', 'viewBox', `${bgBbox.x} ${bgBbox.y} ${bgBbox.width} ${bgBbox.height}`);
            }
            svgBackground.setAttributeNS('http://www.w3.org/2000/svg', 'preserveAspectRatio', 'none');
            svgBackground.appendChild(el);
            svgDocumentElement.appendChild(svgBackground);
        });

        defsEl.appendChild(path);
        // Setting the clip path for use and for preview
        const useClipPathEl = document.createElementNS('http://www.w3.org/2000/svg', 'use');
        useClipPathEl.setAttributeNS('http://www.w3.org/1999/xlink', 'href', '#filterPath');
        useClipPathEl.setAttribute('fill', 'none');
        clipPathEl.appendChild(useClipPathEl);

        const svgPreviewEl = svg.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svgPreviewEl.setAttributeNS('http://www.w3.org/2000/svg', 'viewBox', '0 0 1 1');
        svgPreviewEl.setAttribute('width', '600');
        svgPreviewEl.setAttribute('height', '600');
        svgPreviewEl.setAttribute('id', 'preview');
        svgPreviewEl.setAttributeNS('http://www.w3.org/2000/svg', 'preserveAspectRatio', 'none');
        const previewUseEl = useClipPathEl.cloneNode(true);
        previewUseEl.setAttribute('fill', 'darkgrey');
        svgPreviewEl.appendChild(previewUseEl);
        svgDocumentElement.appendChild(svgPreviewEl);

        const imageEl = document.createElement('image');
        imageEl.setAttribute('xlink:href', '');
        imageEl.setAttribute('clip-path', 'url(#clip-path)');
        svgDocumentElement.appendChild(imageEl);
        // Give a default size to the SVGs for an easier preview on disk
        svgDocumentElement.setAttribute('width', '600');
        svgDocumentElement.setAttribute('height', '600');

        const outFile = new File([svgDocumentElement.outerHTML], filePicker.files[0].name, { type: 'image/svg+xml' });
        const outFileReader = new FileReader();
        const outReaderPromise = new Promise((resolve, reject) => {
            outFileReader.addEventListener('load', () => resolve(outFileReader.result));
            outFileReader.addEventListener('error', () => reject(outFileReader.error));
        });
        outFileReader.readAsDataURL(outFile);
        const dataURL = await outReaderPromise;

        const downloadLinkEl = document.createElement('a');
        downloadLinkEl.href = dataURL;
        downloadLinkEl.innerText = 'Download';
        downloadLinkEl.setAttribute('download', file.name);
        downloadLinkEl.classList.add('dl_link');
        document.getElementById('downloadArea').appendChild(downloadLinkEl);
    });
});
