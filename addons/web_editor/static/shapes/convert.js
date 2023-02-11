/* eslint-env node */
/*
The following script can be used to convert SVGs exported from illustrator into
a format that's compatible with the shape system. It runs with nodejs. Some
manual conversion may be necessary.

FIXME this script is out-dated.
*/

const fs = require('fs');
const path = require('path');

const palette = {
    '1': '#3AADAA',
    '2': '#7C6576',
    '3': '#F6F6F6',
    '4': '#FFFFFF',
    '5': '#383E45',
};

const positions = ['top', 'left', 'bottom', 'right', 'center', 'stretch'];

const directories = fs.readdirSync(__dirname).filter(nodeName => {
    return nodeName[0] !== '.' && fs.lstatSync(path.join(__dirname, nodeName)).isDirectory();
});
const files = directories.flatMap(dirName => {
    return fs.readdirSync(path.join(__dirname, dirName))
        .filter(fileName => fileName.endsWith('.svg'))
        .map(fileName => path.join(__dirname, dirName, fileName));
});

const shapes = [];
files.filter(f => f.endsWith('svg')).forEach(filePath => {
    const svg = String(fs.readFileSync(filePath));
    const fileName = filePath.match(/([^/]+)$/)[1];

    const colors = svg.match(/#[0-9A-F]{3,}/gi);
    const nonPaletteColors = colors && colors.filter(color => !Object.values(palette).includes(color.toUpperCase()));
    const shape = {
        svg,
        name: fileName.split(/[.-]/)[0],
        page: filePath.slice(__dirname.length + 1, -fileName.length - 1),
        colors: Object.keys(palette).filter(num => new RegExp(palette[num], 'i').test(svg)),
        position: positions.filter(pos => fileName.includes(pos)),
        nonIsometric: fileName.includes('+'),
        nonPaletteColors: nonPaletteColors && nonPaletteColors.length ? nonPaletteColors.join(' ') : null,
        containsImage: svg.includes('<image'),
        repeatX: fileName.includes('repeatx'),
        repeatY: fileName.includes('repeaty'),
    };
    shape.optionXML = `<we-button data-shape="web_editor/${shape.page}/${shape.name}" data-select-label="${shape.page} ${shape.name}"/>`;
    if (shape.position[0] === 'stretch') {
        shape.position = ['center'];
        shape.size = '100% 100%';
    } else {
        shape.size = '100% auto';
    }
    shape.scss = `'${shape.page}/${shape.name}': ('position': ${shape.position[0]}, 'size': ${shape.size}, 'colors': (${shape.colors.join(', ')})${shape.repeatX ? ", 'repeat-x': true" : ""}${shape.repeatY ? ", 'repeat-y': true" : ""})`;
    shapes.push(shape);
});
const xml = shapes.map(shape => shape.optionXML).join('\n');
const scss = shapes.map(shape => shape.scss).join(',\n');
const nonConformShapes = shapes.flatMap(shape => {
    const violations = {};
    let invalid = false;
    // Not sure if we want this check, edi still trying to see if she can do shadows without embedding PNGs
    // if (shape.containsImage) {
    //     violations.containsImage = shape.containsImage;
    //     invalid = true;
    // }
    if (shape.nonIsometric) {
        violations.nonIsometric = shape.nonIsometric;
        invalid = true;
    }
    if (shape.nonPaletteColors) {
        violations.nonPaletteColors = shape.nonPaletteColors;
        invalid = true;
    }
    if (shape.position.length > 1 || shape.position.length == 0) {
        violations.position = shape.position;
        invalid = true;
    }
    if (!invalid) {
        return []
    }
    return [[shape, violations]];
});
console.log('The following shapes are not conform:', nonConformShapes);

const convertDir = './.converted';
fs.mkdirSync(convertDir);
const convertedPath = path.join(__dirname, convertDir);
fs.writeFileSync(path.join(convertedPath, 'options.xml'), xml);
fs.writeFileSync(path.join(convertedPath, 'variables.scss'), scss);
shapes.forEach(shape => {
    const pageDir = path.join(convertedPath, shape.page);
    if (!fs.existsSync(pageDir)) {
        fs.mkdirSync(pageDir);
    }
    fs.writeFileSync(path.join(pageDir, shape.name + '.svg'), shape.svg);
});
