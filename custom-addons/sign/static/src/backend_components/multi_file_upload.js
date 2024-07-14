/** @odoo-module **/

const addNewFiles = (files) => {
    sessionStorage.setItem("signMultiFileData", JSON.stringify(files));
    return true;
};

const getNext = () => {
    return (JSON.parse(sessionStorage.getItem("signMultiFileData")) || []).shift();
};

const removeFile = (id) => {
    const files = JSON.parse(sessionStorage.getItem("signMultiFileData")) || [];
    sessionStorage.setItem(
        "signMultiFileData",
        JSON.stringify(
            files.reduce((files, file) => {
                if (file.template === id) {
                    return files;
                }
                files.push(file);
                return files;
            }, [])
        )
    );
};

export const multiFileUpload = {
    addNewFiles: addNewFiles,
    getNext: getNext,
    removeFile: removeFile,
};
export default multiFileUpload;
