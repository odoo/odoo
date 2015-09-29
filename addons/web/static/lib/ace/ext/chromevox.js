define(function(require, exports, module) {

/* ChromeVox Ace namespace. */
var cvoxAce = {};

/* Typedefs for Closure compiler. */
/**
 * @typedef {{
    rate: number,
    pitch: number,
    volume: number,
    relativePitch: number,
    punctuationEcho: string
   }}
 */
/* TODO(peterxiao): Export this typedef through cvox.Api. */
cvoxAce.SpeechProperty;

/**
 * @typedef {{
 *   row: number,
 *   column: number
 * }}
 */
cvoxAce.Cursor;

/**
 * @typedef {{
    type: string,
    value: string
   }}
 }
 */
cvoxAce.Token;

/**
 * These are errors and information that Ace will display in the gutter.
 * @typedef {{
    row: number,
    column: number,
    value: string
   }}
 }
 */
cvoxAce.Annotation;

/* Speech Properties. */
/**
 * Speech property for speaking constant tokens.
 * @type {cvoxAce.SpeechProperty}
 */
var CONSTANT_PROP = {
  'rate': 0.8,
  'pitch': 0.4,
  'volume': 0.9
};

/**
 * Default speech property for speaking tokens.
 * @type {cvoxAce.SpeechProperty}
 */
var DEFAULT_PROP = {
  'rate': 1,
  'pitch': 0.5,
  'volume': 0.9
};

/**
 * Speech property for speaking entity tokens.
 * @type {cvoxAce.SpeechProperty}
 */
var ENTITY_PROP = {
  'rate': 0.8,
  'pitch': 0.8,
  'volume': 0.9
};

/**
 * Speech property for speaking keywords.
 * @type {cvoxAce.SpeechProperty}
 */
var KEYWORD_PROP = {
  'rate': 0.8,
  'pitch': 0.3,
  'volume': 0.9
};

/**
 * Speech property for speaking storage tokens.
 * @type {cvoxAce.SpeechProperty}
 */
var STORAGE_PROP = {
  'rate': 0.8,
  'pitch': 0.7,
  'volume': 0.9
};

/**
 * Speech property for speaking variable tokens.
 * @type {cvoxAce.SpeechProperty}
 */
var VARIABLE_PROP = {
  'rate': 0.8,
  'pitch': 0.8,
  'volume': 0.9
};

/**
 * Speech property for speaking deleted text.
 * @type {cvoxAce.SpeechProperty}
 */
var DELETED_PROP = {
  'punctuationEcho': 'none',
  'relativePitch': -0.6
};

/* Constants for Earcons. */
var ERROR_EARCON = 'ALERT_NONMODAL';
var MODE_SWITCH_EARCON = 'ALERT_MODAL';
var NO_MATCH_EARCON = 'INVALID_KEYPRESS';

/* Constants for vim state. */
var INSERT_MODE_STATE = 'insertMode';
var COMMAND_MODE_STATE = 'start';

var REPLACE_LIST = [
  {
    substr: ';',
    newSubstr: ' semicolon '
  },
  {
    substr: ':',
    newSubstr: ' colon '
  }
];

/**
 * Context menu commands.
 */
var Command = {
  SPEAK_ANNOT: 'annots',
  SPEAK_ALL_ANNOTS: 'all_annots',
  TOGGLE_LOCATION: 'toggle_location',
  SPEAK_MODE: 'mode',
  SPEAK_ROW_COL: 'row_col',
  TOGGLE_DISPLACEMENT: 'toggle_displacement',
  FOCUS_TEXT: 'focus_text'
};

/**
 * Key prefix for each shortcut.
 */
var KEY_PREFIX = 'CONTROL + SHIFT ';

/* Globals. */
cvoxAce.editor = null;
/**
 * Last cursor position.
 * @type {cvoxAce.Cursor}
 */
var lastCursor = null;

/**
 * Table of annotations.
 * @typedef {!Object.<number, Object<number, cvoxAce.Annotation>>}
 */
var annotTable = {};

/**
 * Whether to speak character, word, and then line. This allows blind users
 * to know the location of the cursor when they change lines.
 * @typedef {boolean}
 */
var shouldSpeakRowLocation = false;

/**
 * Whether to speak displacement.
 * @typedef {boolean}
 */
var shouldSpeakDisplacement = false;

/**
 * Whether text was changed to cause a cursor change event.
 * @typedef {boolean}
 */
var changed = false;

/**
 * Current state vim is in.
 */
var vimState = null;

/**
 * Mapping from key code to shortcut.
 */
var keyCodeToShortcutMap = {};

/**
 * Mapping from command to shortcut.
 */
var cmdToShortcutMap = {};

/**
 * Get shortcut string from keyCode.
 * @param {number} keyCode Key code of shortcut.
 * @return {string} String representation of shortcut.
 */
var getKeyShortcutString = function(keyCode) {
  return KEY_PREFIX + String.fromCharCode(keyCode);
};

/**
 * Return if in vim mode.
 * @return {boolean} True if in Vim mode.
 */
var isVimMode = function() {
  var keyboardHandler = cvoxAce.editor.keyBinding.getKeyboardHandler();
  return keyboardHandler.$id === 'ace/keyboard/vim';
};

/**
 * Gets the current token.
 * @param {!cvoxAce.Cursor} cursor Current position of the cursor.
 * @return {!cvoxAce.Token} Token at the current position.
 */
var getCurrentToken = function(cursor) {
  return cvoxAce.editor.getSession().getTokenAt(cursor.row, cursor.column + 1);
};

/**
 * Gets the current line the cursor is under.
 * @param {!cvoxAce.Cursor} cursor Current cursor position.
 */
var getCurrentLine = function(cursor) {
  return cvoxAce.editor.getSession().getLine(cursor.row);
};

/**
 * Event handler for row changes. When the user changes rows we want to speak
 * the line so the user can work on this line. If shouldSpeakRowLocation is on
 * then we speak the character, then the row, then the line so the user knows
 * where the cursor is.
 * @param {!cvoxAce.Cursor} currCursor Current cursor position.
 */
var onRowChange = function(currCursor) {
  /* Notify that this line has an annotation. */
  if (annotTable[currCursor.row]) {
    cvox.Api.playEarcon(ERROR_EARCON);
  }
  if (shouldSpeakRowLocation) {
    cvox.Api.stop();
    speakChar(currCursor);
    speakTokenQueue(getCurrentToken(currCursor));
    speakLine(currCursor.row, 1);
  } else {
    speakLine(currCursor.row, 0);
  }
};

/**
 * Returns whether the cursor is at the beginning of a word. A word is
 * a grouping of alphanumeric characters including underscores.
 * @param {!cvoxAce.Cursor} cursor Current cursor position.
 * @return {boolean} Whether there is word.
 */
var isWord = function(cursor) {
  var line = getCurrentLine(cursor);
  var lineSuffix = line.substr(cursor.column - 1);
  if (cursor.column === 0) {
    lineSuffix = ' ' + line;
  }
  /* Use regex to tell if the suffix is at the start of a new word. */
  var firstWordRegExp = /^\W(\w+)/;
  var words = firstWordRegExp.exec(lineSuffix);
  return words !== null;
};

/**
 * A mapping of syntax type to speech properties / expanding rules.
 */
var rules = {
  'constant': {
    prop: CONSTANT_PROP
  },
  'entity': {
    prop: ENTITY_PROP
  },
  'keyword': {
    prop: KEYWORD_PROP
  },
  'storage': {
    prop: STORAGE_PROP
  },
  'variable': {
    prop: VARIABLE_PROP
  },
  'meta': {
    prop: DEFAULT_PROP,
    replace: [
      {
        substr: '</',
        newSubstr: ' closing tag '
      },
      {
        substr: '/>',
        newSubstr: ' close tag '
      },
      {
        substr: '<',
        newSubstr: ' tag start '
      },
      {
        substr: '>',
        newSubstr: ' tag end '
      }
    ]
  }
};

/**
 * Default rule to be used.
 */
var DEFAULT_RULE = {
  prop: DEFAULT_RULE
};

/**
 * Expands substrings to how they are read based on the given rules.
 * @param {string} value Text to be expanded.
 * @param {Array.<Object>} replaceRules Rules to determine expansion.
 * @return {string} New expanded value.
 */
var expand = function(value, replaceRules) {
  var newValue = value;
  for (var i = 0; i < replaceRules.length; i++) {
    var replaceRule = replaceRules[i];
    var regexp = new RegExp(replaceRule.substr, 'g');
    newValue = newValue.replace(regexp, replaceRule.newSubstr);
  }
  return newValue;
};

/**
 * Merges tokens from start inclusive to end exclusive.
 * @param {Array.<cvoxAce.Token>} Tokens to be merged.
 * @param {number} start Start index inclusive.
 * @param {number} end End index exclusive.
 * @return {cvoxAce.Token} Merged token.
 */
var mergeTokens = function(tokens, start, end) {
  /* Different type of token found! Merge all previous like tokens. */
  var newToken = {};
  newToken.value = '';
  newToken.type = tokens[start].type;
  for (var j = start; j < end; j++) {
    newToken.value += tokens[j].value;
  }
  return newToken;
};

/**
 * Merges tokens that use the same speech properties.
 * @param {Array.<cvoxAce.Token>} tokens Tokens to be merged.
 * @return {Array.<cvoxAce.Token>} Merged tokens.
 */
var mergeLikeTokens = function(tokens) {
  if (tokens.length <= 1) {
    return tokens;
  }
  var newTokens = [];
  var lastLikeIndex = 0;
  for (var i = 1; i < tokens.length; i++) {
    var lastLikeToken = tokens[lastLikeIndex];
    var currToken = tokens[i];
    if (getTokenRule(lastLikeToken) !== getTokenRule(currToken)) {
      newTokens.push(mergeTokens(tokens, lastLikeIndex, i));
      lastLikeIndex = i;
    }
  }
  newTokens.push(mergeTokens(tokens, lastLikeIndex, tokens.length));
  return newTokens;
};

/**
 * Returns if given row is a whitespace row.
 * @param {number} row Row.
 * @return {boolean} True if row is whitespaces.
 */
var isRowWhiteSpace = function(row) {
  var line = cvoxAce.editor.getSession().getLine(row);
  var whiteSpaceRegexp = /^\s*$/;
  return whiteSpaceRegexp.exec(line) !== null;
};

/**
 * Speak the line with syntax properties.
 * @param {number} row Row to speak.
 * @param {number} queue Queue mode to speak.
 */
var speakLine = function(row, queue) {
  var tokens = cvoxAce.editor.getSession().getTokens(row);
  if (tokens.length === 0 || isRowWhiteSpace(row)) {
    cvox.Api.playEarcon('EDITABLE_TEXT');
    return;
  }
  tokens = mergeLikeTokens(tokens);
  var firstToken = tokens[0];
  /* Filter out first token. */
  tokens = tokens.filter(function(token) {
    return token !== firstToken;
  });
  /* Speak first token separately to flush if queue. */
  speakToken_(firstToken, queue);
  /* Speak rest of tokens. */
  tokens.forEach(speakTokenQueue);
};

/**
 * Speak the token based on the syntax of the token, flushing.
 * @param {!cvoxAce.Token} token Token to speak.
 * @param {number} queue Queue mode.
 */
var speakTokenFlush = function(token) {
  speakToken_(token, 0);
};

/**
 * Speak the token based on the syntax of the token, queueing.
 * @param {!cvoxAce.Token} token Token to speak.
 * @param {number} queue Queue mode.
 */
var speakTokenQueue = function(token) {
  speakToken_(token, 1);
};

/**
 * @param {!cvoxAce.Token} token Token to speak.
 * Get the token speech property.
 */
var getTokenRule = function(token) {
  /* Types are period delimited. In this case, we only syntax speak the outer
   * most type of token. */
  if (!token || !token.type) {
    return;
  }
  var split = token.type.split('.');
  if (split.length === 0) {
    return;
  }
  var type = split[0];
  var rule = rules[type];
  if (!rule) {
    return DEFAULT_RULE;
  }
  return rule;
};

/**
 * Speak the token based on the syntax of the token.
 * @private
 * @param {!cvoxAce.Token} token Token to speak.
 * @param {number} queue Queue mode.
 */
var speakToken_ = function(token, queue) {
  var rule = getTokenRule(token);
  var value = expand(token.value, REPLACE_LIST);
  if (rule.replace) {
    value = expand(value, rule.replace);
  }
  cvox.Api.speak(value, queue, rule.prop);
};

/**
 * Speaks the character under the cursor. This is queued.
 * @param {!cvoxAce.Cursor} cursor Current cursor position.
 * @return {string} Character.
 */
var speakChar = function(cursor) {
  var line = getCurrentLine(cursor);
  cvox.Api.speak(line[cursor.column], 1);
};

/**
 * Speaks the jump from lastCursor to currCursor. This function assumes the
 * jump takes place on the current line.
 * @param {!cvoxAce.Cursor} lastCursor Previous cursor position.
 * @param {!cvoxAce.Cursor} currCursor Current cursor position.
 */
var speakDisplacement = function(lastCursor, currCursor) {
  var line = getCurrentLine(currCursor);

  /* Get the text that we jumped past. */
  var displace = line.substring(lastCursor.column, currCursor.column);

  /* Speak out loud spaces. */
  displace = displace.replace(/ /g, ' space ');
  cvox.Api.speak(displace);
};

/**
 * Speaks the word if the cursor jumped to a new word or to the beginning
 * of the line. Otherwise speak the charactor.
 * @param {!cvoxAce.Cursor} lastCursor Previous cursor position.
 * @param {!cvoxAce.Cursor} currCursor Current cursor position.
 */
var speakCharOrWordOrLine = function(lastCursor, currCursor) {
  /* Say word only if jump. */
  if (Math.abs(lastCursor.column - currCursor.column) !== 1) {
    var currLineLength = getCurrentLine(currCursor).length;
    /* Speak line if jumping to beginning or end of line. */
    if (currCursor.column === 0 || currCursor.column === currLineLength) {
      speakLine(currCursor.row, 0);
      return;
    }
    if (isWord(currCursor)) {
      cvox.Api.stop();
      speakTokenQueue(getCurrentToken(currCursor));
      return;
    }
  }
  speakChar(currCursor);
};

/**
 * Event handler for column changes. If shouldSpeakDisplacement is on, then
 * we just speak displacements in row changes. Otherwise, we either speak
 * the character for single character movements, the word when jumping to the
 * next word, or the entire line if jumping to beginning or end of the line.
 * @param {!cvoxAce.Cursor} lastCursor Previous cursor position.
 * @param {!cvoxAce.Cursor} currCursor Current cursor position.
 */
var onColumnChange = function(lastCursor, currCursor) {
  if (!cvoxAce.editor.selection.isEmpty()) {
    speakDisplacement(lastCursor, currCursor);
    cvox.Api.speak('selected', 1);
  }
  else if (shouldSpeakDisplacement) {
    speakDisplacement(lastCursor, currCursor);
  } else {
    speakCharOrWordOrLine(lastCursor, currCursor);
  }
};

/**
 * Event handler for cursor changes. Classify cursor changes as either row or
 * column changes, then delegate accordingly.
 * @param {!Event} evt The event.
 */
var onCursorChange = function(evt) {
  /* Do not speak if cursor change was a result of text insertion. We want to
   * speak the text that was inserted and not where the cursor lands. */
  if (changed) {
    changed = false;
    return;
  }
  var currCursor = cvoxAce.editor.selection.getCursor();
  if (currCursor.row !== lastCursor.row) {
    onRowChange(currCursor);
  } else {
    onColumnChange(lastCursor, currCursor);
  }
  lastCursor = currCursor;
};

/**
 * Event handler for selection changes.
 * @param {!Event} evt The event.
 */
var onSelectionChange = function(evt) {
  /* Assumes that when selection changes to empty, the user has unselected. */
  if (cvoxAce.editor.selection.isEmpty()) {
    cvox.Api.speak('unselected');
  }
};

/**
 * Event handler for source changes. We want auditory feedback for inserting
 * and deleting text.
 * @param {!Event} evt The event.
 */
var onChange = function(delta) {
  switch (data.action) {
  case 'remove':
    cvox.Api.speak(data.text, 0, DELETED_PROP);
    /* Let the future cursor change event know it's from text change. */
    changed = true;
    break;
  case 'insert':
    cvox.Api.speak(data.text, 0);
    /* Let the future cursor change event know it's from text change. */
    changed = true;
    break;
  }
};

/**
 * Returns whether or not the annotation is new.
 * @param {!cvoxAce.Annotation} annot Annotation in question.
 * @return {boolean} Whether annot is new.
 */
var isNewAnnotation = function(annot) {
  var row = annot.row;
  var col = annot.column;
  return !annotTable[row] || !annotTable[row][col];
};

/**
 * Populates the annotation table.
 * @param {!Array.<cvoxAce.Annotation>} annotations Array of annotations.
 */
var populateAnnotations = function(annotations) {
  annotTable = {};
  for (var i = 0; i < annotations.length; i++) {
    var annotation = annotations[i];
    var row = annotation.row;
    var col = annotation.column;
    if (!annotTable[row]) {
      annotTable[row] = {};
    }
    annotTable[row][col] = annotation;
  }
};

/**
 * Event handler for annotation changes. We want to notify the user when an
 * a new annotation appears.
 * @param {!Event} evt Event.
 */
var onAnnotationChange = function(evt) {
  var annotations = cvoxAce.editor.getSession().getAnnotations();
  var newAnnotations = annotations.filter(isNewAnnotation);
  if (newAnnotations.length > 0) {
    cvox.Api.playEarcon(ERROR_EARCON);
  }
  populateAnnotations(annotations);
};

/**
 * Speak annotation.
 * @param {!cvoxAce.Annotation} annot Annotation to speak.
 */
var speakAnnot = function(annot) {
  var annotText = annot.type + ' ' + annot.text + ' on ' +
      rowColToString(annot.row, annot.column);
  annotText = annotText.replace(';', 'semicolon');
  cvox.Api.speak(annotText, 1);
};

/**
 * Speak annotations in a row.
 * @param {number} row Row of annotations to speak.
 */
var speakAnnotsByRow = function(row) {
  var annots = annotTable[row];
  for (var col in annots) {
    speakAnnot(annots[col]);
  }
};

/**
 * Get a string representation of a row and column.
 * @param {boolean} row Zero indexed row.
 * @param {boolean} col Zero indexed column.
 * @return {string} Row and column to be spoken.
 */
var rowColToString = function(row, col) {
  return 'row ' + (row + 1) + ' column ' + (col + 1);
};

/**
 * Speaks the row and column.
 */
var speakCurrRowAndCol = function() {
  cvox.Api.speak(rowColToString(lastCursor.row, lastCursor.column));
};

/**
 * Speaks all annotations.
 */
var speakAllAnnots = function() {
  for (var row in annotTable) {
    speakAnnotsByRow(row);
  }
};

/**
 * Speak the vim mode. If no vim mode, this function does nothing.
 */
var speakMode = function() {
  if (!isVimMode()) {
    return;
  }
  switch (cvoxAce.editor.keyBinding.$data.state) {
  case INSERT_MODE_STATE:
    cvox.Api.speak('Insert mode');
    break;
  case COMMAND_MODE_STATE:
    cvox.Api.speak('Command mode');
    break;
  }
};

/**
 * Toggle speak location.
 */
var toggleSpeakRowLocation = function() {
  shouldSpeakRowLocation = !shouldSpeakRowLocation;
  /* Auditory feedback of the change. */
  if (shouldSpeakRowLocation) {
    cvox.Api.speak('Speak location on row change enabled.');
  } else {
    cvox.Api.speak('Speak location on row change disabled.');
  }
};

/**
 * Toggle speak displacement.
 */
var toggleSpeakDisplacement = function() {
  shouldSpeakDisplacement = !shouldSpeakDisplacement;
  /* Auditory feedback of the change. */
  if (shouldSpeakDisplacement) {
    cvox.Api.speak('Speak displacement on column changes.');
  } else {
    cvox.Api.speak('Speak current character or word on column changes.');
  }
};

/**
 * Event handler for key down events. Gets the right shortcut from the map,
 * and calls the associated function.
 * @param {!Event} evt Keyboard event.
 */
var onKeyDown = function(evt) {
  if (evt.ctrlKey && evt.shiftKey) {
    var shortcut = keyCodeToShortcutMap[evt.keyCode];
    if (shortcut) {
      shortcut.func();
    }
  }
};

/**
 * Event handler for status change events. Auditory feedback of changing
 * between vim states.
 * @param {!Event} evt Change status event.
 * @param {!Object} editor Editor state.
 */
var onChangeStatus = function(evt, editor) {
  if (!isVimMode()) {
    return;
  }
  var state = editor.keyBinding.$data.state;
  if (state === vimState) {
    /* State hasn't changed, do nothing. */
    return;
  }
  switch (state) {
  case INSERT_MODE_STATE:
    cvox.Api.playEarcon(MODE_SWITCH_EARCON);
    /* When in insert mode, we want to speak out keys as feedback. */
    cvox.Api.setKeyEcho(true);
    break;
  case COMMAND_MODE_STATE:
    cvox.Api.playEarcon(MODE_SWITCH_EARCON);
    /* When in command mode, we want don't speak out keys because those keys
    * are not being inserted in the document. */
    cvox.Api.setKeyEcho(false);
    break;
  }
  vimState = state;
};

/**
 * Handles context menu events. This is a ChromeVox feature where hitting
 * the shortcut ChromeVox + comma will open up a search bar where you can
 * type in various commands. All keyboard shortcuts are also commands that
 * can be invoked. This handles the event that ChromeVox sends to the page.
 * @param {Event} evt Event received.
 */
var contextMenuHandler = function(evt) {
  var cmd = evt.detail['customCommand'];
  var shortcut = cmdToShortcutMap[cmd];
  if (shortcut) {
    shortcut.func();
    /* ChromeVox will bring focus to an element near the cursor instead of the
     * text input. */
    cvoxAce.editor.focus();
  }
};

/**
 * Initialize the ChromeVox context menu.
 */
var initContextMenu = function() {
  var ACTIONS = SHORTCUTS.map(function(shortcut) {
    return {
      desc: shortcut.desc + getKeyShortcutString(shortcut.keyCode),
      cmd: shortcut.cmd
    };
  });

  /* Attach ContextMenuActions. */
  var body = document.querySelector('body');
  body.setAttribute('contextMenuActions', JSON.stringify(ACTIONS));

  /* Listen for ContextMenu events. */
  body.addEventListener('ATCustomEvent', contextMenuHandler, true);
};

/**
 * Event handler for find events. When there is a match, we want to speak the
 * line we are now at. Otherwise, we want to notify the user there was no
 * match
 * @param {!Event} evt The event.
 */
var onFindSearchbox = function(evt) {
  if (evt.match) {
    /* There is still a match! Speak the line. */
    speakLine(lastCursor.row, 0);
  } else {
    /* No match, give auditory feedback! */
    cvox.Api.playEarcon(NO_MATCH_EARCON);
  }
};

/**
 * Focus to text input.
 */
var focus = function() {
  cvoxAce.editor.focus();
};

/**
 * Shortcut definitions.
 */
var SHORTCUTS = [
  {
    /* 1 key. */
    keyCode: 49,
    func: function() {
      speakAnnotsByRow(lastCursor.row);
    },
    cmd: Command.SPEAK_ANNOT,
    desc: 'Speak annotations on line'
  },
  {
    /* 2 key. */
    keyCode: 50,
    func: speakAllAnnots,
    cmd: Command.SPEAK_ALL_ANNOTS,
    desc: 'Speak all annotations'
  },
  {
    /* 3 key. */
    keyCode: 51,
    func: speakMode,
    cmd: Command.SPEAK_MODE,
    desc: 'Speak Vim mode'
  },
  {
    /* 4 key. */
    keyCode: 52,
    func: toggleSpeakRowLocation,
    cmd: Command.TOGGLE_LOCATION,
    desc: 'Toggle speak row location'
  },
  {
    /* 5 key. */
    keyCode: 53,
    func: speakCurrRowAndCol,
    cmd: Command.SPEAK_ROW_COL,
    desc: 'Speak row and column'
  },
  {
    /* 6 key. */
    keyCode: 54,
    func: toggleSpeakDisplacement,
    cmd: Command.TOGGLE_DISPLACEMENT,
    desc: 'Toggle speak displacement'
  },
  {
    /* 7 key. */
    keyCode: 55,
    func: focus,
    cmd: Command.FOCUS_TEXT,
    desc: 'Focus text'
  }
];

/**
 * Event handler for focus events.
 */
var onFocus = function() {
  cvoxAce.editor = editor;

  /* Set up listeners. */
  editor.getSession().selection.on('changeCursor', onCursorChange);
  editor.getSession().selection.on('changeSelection', onSelectionChange);
  editor.getSession().on('change', onChange);
  editor.getSession().on('changeAnnotation', onAnnotationChange);
  editor.on('changeStatus', onChangeStatus);
  editor.on('findSearchBox', onFindSearchbox);
  editor.container.addEventListener('keydown', onKeyDown);

  lastCursor = editor.selection.getCursor();
};

/**
 * Initialize the theme.
 * @param {Object} editor Editor to use.
 */
var init = function(editor) {
  onFocus();

  /* Construct maps. */
  SHORTCUTS.forEach(function(shortcut) {
    keyCodeToShortcutMap[shortcut.keyCode] = shortcut;
    cmdToShortcutMap[shortcut.cmd] = shortcut;
  });

  editor.on('focus', onFocus);

  /* Assume we start in command mode if vim. */
  if (isVimMode()) {
    cvox.Api.setKeyEcho(false);
  }
  initContextMenu();
};

/**
 * Returns if cvox exists, and the api exists.
 * @return {boolean} Whether not Cvox Api exists.
 */
function cvoxApiExists() {
  return (typeof(cvox) !== 'undefined') && cvox && cvox.Api;
}

/**
 * Number of tries for Cvox loading.
 * @type {number}
 */
var tries = 0;

/**
 * Max number of tries to watch for Cvox loading.
 * @type {number}
 */
var MAX_TRIES = 15;

/**
 * Check for ChromeVox load.
 * @param {Object} editor Editor to use.
 */
function watchForCvoxLoad(editor) {
  if (cvoxApiExists()) {
    init(editor);
  } else {
    tries++;
    if (tries >= MAX_TRIES) {
      return;
    }
    window.setTimeout(watchForCvoxLoad, 500, editor);
  }
}

var Editor = require('../editor').Editor;
require('../config').defineOptions(Editor.prototype, 'editor', {
  enableChromevoxEnhancements: {
    set: function(val) {
      if (val) {
        watchForCvoxLoad(this);
      }
    },
    value: true // turn it on by default or check for window.cvox
  }
});

});
