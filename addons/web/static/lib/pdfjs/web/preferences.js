/* -*- Mode: Java; tab-width: 2; indent-tabs-mode: nil; c-basic-offset: 2 -*- */
/* vim: set shiftwidth=2 tabstop=2 autoindent cindent expandtab: */
/* Copyright 2013 Mozilla Foundation
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
/* globals DEFAULT_PREFERENCES, Promise */

'use strict';

//#include default_preferences.js

var SidebarView = {
  NONE: 0,
  THUMBS: 1,
  OUTLINE: 2,
  ATTACHMENTS: 3
};

/**
 * Preferences - Utility for storing persistent settings.
 *   Used for settings that should be applied to all opened documents,
 *   or every time the viewer is loaded.
 */
var Preferences = {
  prefs: Object.create(DEFAULT_PREFERENCES),
  isInitializedPromiseResolved: false,
  initializedPromise: null,

  /**
   * Initialize and fetch the current preference values from storage.
   * @return {Promise} A promise that is resolved when the preferences
   *                   have been initialized.
   */
  initialize: function preferencesInitialize() {
    return this.initializedPromise =
        this._readFromStorage(DEFAULT_PREFERENCES).then(function(prefObj) {
      this.isInitializedPromiseResolved = true;
      if (prefObj) {
        this.prefs = prefObj;
      }
    }.bind(this));
  },

  /**
   * Stub function for writing preferences to storage.
   * NOTE: This should be overridden by a build-specific function defined below.
   * @param {Object} prefObj The preferences that should be written to storage.
   * @return {Promise} A promise that is resolved when the preference values
   *                   have been written.
   */
  _writeToStorage: function preferences_writeToStorage(prefObj) {
    return Promise.resolve();
  },

  /**
   * Stub function for reading preferences from storage.
   * NOTE: This should be overridden by a build-specific function defined below.
   * @param {Object} prefObj The preferences that should be read from storage.
   * @return {Promise} A promise that is resolved with an {Object} containing
   *                   the preferences that have been read.
   */
  _readFromStorage: function preferences_readFromStorage(prefObj) {
    return Promise.resolve();
  },

  /**
   * Reset the preferences to their default values and update storage.
   * @return {Promise} A promise that is resolved when the preference values
   *                   have been reset.
   */
  reset: function preferencesReset() {
    return this.initializedPromise.then(function() {
      this.prefs = Object.create(DEFAULT_PREFERENCES);
      return this._writeToStorage(DEFAULT_PREFERENCES);
    }.bind(this));
  },

  /**
   * Replace the current preference values with the ones from storage.
   * @return {Promise} A promise that is resolved when the preference values
   *                   have been updated.
   */
  reload: function preferencesReload() {
    return this.initializedPromise.then(function () {
      this._readFromStorage(DEFAULT_PREFERENCES).then(function(prefObj) {
        if (prefObj) {
          this.prefs = prefObj;
        }
      }.bind(this));
    }.bind(this));
  },

  /**
   * Set the value of a preference.
   * @param {string} name The name of the preference that should be changed.
   * @param {boolean|number|string} value The new value of the preference.
   * @return {Promise} A promise that is resolved when the value has been set,
   *                   provided that the preference exists and the types match.
   */
  set: function preferencesSet(name, value) {
    return this.initializedPromise.then(function () {
      if (DEFAULT_PREFERENCES[name] === undefined) {
        throw new Error('preferencesSet: \'' + name + '\' is undefined.');
      } else if (value === undefined) {
        throw new Error('preferencesSet: no value is specified.');
      }
      var valueType = typeof value;
      var defaultType = typeof DEFAULT_PREFERENCES[name];

      if (valueType !== defaultType) {
        if (valueType === 'number' && defaultType === 'string') {
          value = value.toString();
        } else {
          throw new Error('Preferences_set: \'' + value + '\' is a \"' +
                          valueType + '\", expected \"' + defaultType + '\".');
        }
      } else {
        if (valueType === 'number' && (value | 0) !== value) {
          throw new Error('Preferences_set: \'' + value +
                          '\' must be an \"integer\".');
        }
      }
      this.prefs[name] = value;
      return this._writeToStorage(this.prefs);
    }.bind(this));
  },

  /**
   * Get the value of a preference.
   * @param {string} name The name of the preference whose value is requested.
   * @return {Promise} A promise that is resolved with a {boolean|number|string}
   *                   containing the value of the preference.
   */
  get: function preferencesGet(name) {
    return this.initializedPromise.then(function () {
      var defaultValue = DEFAULT_PREFERENCES[name];

      if (defaultValue === undefined) {
        throw new Error('preferencesGet: \'' + name + '\' is undefined.');
      } else {
        var prefValue = this.prefs[name];

        if (prefValue !== undefined) {
          return prefValue;
        }
      }
      return defaultValue;
    }.bind(this));
  }
};

//#if B2G
//Preferences._writeToStorage = function (prefObj) {
//  return new Promise(function (resolve) {
//    asyncStorage.setItem('pdfjs.preferences', JSON.stringify(prefObj),
//                         resolve);
//  });
//};
//
//Preferences._readFromStorage = function (prefObj) {
//  return new Promise(function (resolve) {
//    asyncStorage.getItem('pdfjs.preferences', function (prefStr) {
//      var readPrefs = JSON.parse(prefStr);
//      resolve(readPrefs);
//    });
//  });
//};
//#endif

//#if CHROME
//Preferences._writeToStorage = function (prefObj) {
//  return new Promise(function (resolve) {
//    if (prefObj == DEFAULT_PREFERENCES) {
//      var keysToRemove = Object.keys(DEFAULT_PREFERENCES);
//      // If the storage is reset, remove the keys so that the values from
//      // managed storage are applied again.
//      chrome.storage.local.remove(keysToRemove, function() {
//        resolve();
//      });
//    } else {
//      chrome.storage.local.set(prefObj, function() {
//        resolve();
//      });
//    }
//  });
//};
//
//Preferences._readFromStorage = function (prefObj) {
//  return new Promise(function (resolve) {
//    if (chrome.storage.managed) {
//      // Get preferences as set by the system administrator.
//      // See extensions/chromium/preferences_schema.json for more information.
//      // These preferences can be overridden by the user.
//      chrome.storage.managed.get(DEFAULT_PREFERENCES, getPreferences);
//    } else {
//      // Managed storage not supported, e.g. in old Chromium versions.
//      getPreferences(DEFAULT_PREFERENCES);
//    }
//
//    function getPreferences(defaultPrefs) {
//      if (chrome.runtime.lastError) {
//        // Managed storage not supported, e.g. in Opera.
//        defaultPrefs = DEFAULT_PREFERENCES;
//      }
//      chrome.storage.local.get(defaultPrefs, function(readPrefs) {
//        resolve(readPrefs);
//      });
//    }
//  });
//};
//#endif

//#if !(FIREFOX || MOZCENTRAL || B2G || CHROME)
Preferences._writeToStorage = function (prefObj) {
  return new Promise(function (resolve) {
    localStorage.setItem('pdfjs.preferences', JSON.stringify(prefObj));
    resolve();
  });
};

Preferences._readFromStorage = function (prefObj) {
  return new Promise(function (resolve) {
    var readPrefs = JSON.parse(localStorage.getItem('pdfjs.preferences'));
    resolve(readPrefs);
  });
};
//#endif
