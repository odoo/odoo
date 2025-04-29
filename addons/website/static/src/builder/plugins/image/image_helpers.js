export function getShapeURL(shapeName) {
    const [module, directory, fileName] = shapeName.split("/");
    return `/${encodeURIComponent(module)}/static/image_shapes/${encodeURIComponent(
        directory
    )}/${encodeURIComponent(fileName)}.svg`;
}
