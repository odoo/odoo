// marks which axis each parameter of a command belongs to, as well as whether
// it's a positional measurement (x/y), a distance (dx/dy) or none (angles, flags)
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
    document.body.appendChild(svg.documentElement);
    const { x, y, width, height } = svgDocumentElement.getBBox();
    const scalers = toUserSpace(x, y, width, height);

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
    path.setAttribute('fill', 'none');
    svgDocumentElement.removeAttribute('viewBox');
    const clipPath = svgDocumentElement.querySelector('clipPath');

    clipPath.setAttribute('clipPathUnits', 'objectBoundingBox');
    const backgroundEl = svgDocumentElement.getElementById('background');
    const backgroundEls = svgDocumentElement.getElementsByClassName('background')
    Array.from(backgroundEls).forEach(el => {
      const bgBbox = el.getBBox();
      const svgBackground = document.createElement('svg');
      const strokeWidth = el.getAttribute('stroke-width');
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
    // const bgBbox = backgroundEl.getBBox();
    // const svgBackground = document.createElement('svg');
    // const strokeWidth = backgroundEl.getAttribute('stroke-width');
    // if (strokeWidth) {
    //   const adj = parseFloat(strokeWidth) / 2;
    //   svgBackground.setAttributeNS('http://www.w3.org/2000/svg', 'viewBox',
    //   `${bgBbox.x - adj} ${bgBbox.y - adj} ${bgBbox.width + (adj * 2)} ${bgBbox.height + (adj * 2)}`);
    // } else {
    //   svgBackground.setAttributeNS('http://www.w3.org/2000/svg', 'viewBox', `${bgBbox.x} ${bgBbox.y} ${bgBbox.width} ${bgBbox.height}`);
    // }
    // svgBackground.setAttributeNS('http://www.w3.org/2000/svg', 'preserveAspectRatio', 'none');
    // svgBackground.appendChild(backgroundEl);
    // svgDocumentElement.appendChild(svgBackground);

    clipPath.appendChild(path);
    const image = document.createElement('image');
    image.setAttribute('xlink:href', './filter-test.jpeg');
    image.setAttribute('clip-path', 'url(#clip-path)');
    svgDocumentElement.appendChild(image);
    svgDocumentElement.setAttribute('width', '800');
    svgDocumentElement.setAttribute('height', '600');

    const outFile = new File([svgDocumentElement.outerHTML], filePicker.files[0].name, { type: 'image/svg+xml' });
    const outFileReader = new FileReader();
    const outReaderPromise = new Promise((resolve, reject) => {
      outFileReader.addEventListener('load', () => resolve(outFileReader.result));
      outFileReader.addEventListener('error', () => reject(outFileReader.error));
    });
    outFileReader.readAsDataURL(outFile);
    const dataURL = await outReaderPromise;

    const downloadLink = document.createElement('a');
    downloadLink.href = dataURL;
    downloadLink.innerText = 'Download';
    downloadLink.setAttribute('download', 'fixed_' + file.name);
    document.getElementById('downloadArea').appendChild(downloadLink);
  });

});
