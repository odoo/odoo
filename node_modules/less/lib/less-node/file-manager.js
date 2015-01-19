var path = require('path'),
    fs = require('./fs'),
    PromiseConstructor = typeof Promise === 'undefined' ? require('promise') : Promise,
    AbstractFileManager = require("../less/environment/abstract-file-manager.js");

var FileManager = function() {
};

FileManager.prototype = new AbstractFileManager();

FileManager.prototype.supports = function(filename, currentDirectory, options, environment) {
    return true;
};
FileManager.prototype.supportsSync = function(filename, currentDirectory, options, environment) {
    return true;
};

FileManager.prototype.loadFile = function(filename, currentDirectory, options, environment, callback) {
    var fullFilename,
        data;

    options = options || {};

    var paths = [currentDirectory];
    if (options.paths) paths.push.apply(paths, options.paths);
    if (paths.indexOf('.') === -1) paths.push('.');

    if (options.syncImport) {
        var err, result;
        for (var i = 0; i < paths.length; i++) {
            try {
                fullFilename = path.join(paths[i], filename);
                fs.statSync(fullFilename);
                break;
            } catch (e) {
                fullFilename = null;
            }
        }

        if (!fullFilename) {
            err = { type: 'File', message: "'" + filename + "' wasn't found" };
        } else {
            data = fs.readFileSync(fullFilename, 'utf-8');
            result = { contents: data, filename: fullFilename};
        }
        callback(err, result);
        return;
    }

    // promise is guarenteed to be asyncronous
    // which helps as it allows the file handle
    // to be closed before it continues with the next file
    return new PromiseConstructor(function(fulfill, reject) {
        (function tryPathIndex(i) {
            if (i < paths.length) {
                fullFilename = path.join(paths[i], filename);
                fs.stat(fullFilename, function (err) {
                    if (err) {
                        tryPathIndex(i + 1);
                    } else {
                        fs.readFile(fullFilename, 'utf-8', function(e, data) {
                            if (e) { reject(e); return; }

                            fulfill({ contents: data, filename: fullFilename});
                        });
                    }
                });
            } else {
                reject({ type: 'File', message: "'" + filename + "' wasn't found" });
            }
        }(0));
    });
};

FileManager.prototype.loadFileSync = function(filename, currentDirectory, options, environment) {
    filename = path.join(currentDirectory, filename);
    return { contents: fs.readFileSync(filename), filename: filename };
};

module.exports = FileManager;
