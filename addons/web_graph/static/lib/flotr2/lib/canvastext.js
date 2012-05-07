/**
 * This code is released to the public domain by Jim Studt, 2007.
 * He may keep some sort of up to date copy at http://www.federated.com/~jim/canvastext/
 * It as been modified by Fabien Ménager to handle font style like size, weight, color and rotation. 
 * A partial support for special characters has been added too.
 */
var CanvasText = {
  /** The letters definition. It is a list of letters, 
   * with their width, and the coordinates of points compositing them.
   * The syntax for the points is : [x, y], null value means "pen up"
   */
  letters: {
    '\n':{ width: -1, points: [] },
    ' ': { width: 10, points: [] },
    '!': { width: 10, points: [[5,21],[5,7],null,[5,2],[4,1],[5,0],[6,1],[5,2]] },
    '"': { width: 16, points: [[4,21],[4,14],null,[12,21],[12,14]] },
    '#': { width: 21, points: [[11,25],[4,-7],null,[17,25],[10,-7],null,[4,12],[18,12],null,[3,6],[17,6]] },
    '$': { width: 20, points: [[8,25],[8,-4],null,[12,25],[12,-4],null,[17,18],[15,20],[12,21],[8,21],[5,20],[3,18],[3,16],[4,14],[5,13],[7,12],[13,10],[15,9],[16,8],[17,6],[17,3],[15,1],[12,0],[8,0],[5,1],[3,3]] },
    '%': { width: 24, points: [[21,21],[3,0],null,[8,21],[10,19],[10,17],[9,15],[7,14],[5,14],[3,16],[3,18],[4,20],[6,21],[8,21],null,[17,7],[15,6],[14,4],[14,2],[16,0],[18,0],[20,1],[21,3],[21,5],[19,7],[17,7]] },
    '&': { width: 26, points: [[23,12],[23,13],[22,14],[21,14],[20,13],[19,11],[17,6],[15,3],[13,1],[11,0],[7,0],[5,1],[4,2],[3,4],[3,6],[4,8],[5,9],[12,13],[13,14],[14,16],[14,18],[13,20],[11,21],[9,20],[8,18],[8,16],[9,13],[11,10],[16,3],[18,1],[20,0],[22,0],[23,1],[23,2]] },
    '\'':{ width: 10, points: [[5,19],[4,20],[5,21],[6,20],[6,18],[5,16],[4,15]] },
    '(': { width: 14, points: [[11,25],[9,23],[7,20],[5,16],[4,11],[4,7],[5,2],[7,-2],[9,-5],[11,-7]] },
    ')': { width: 14, points: [[3,25],[5,23],[7,20],[9,16],[10,11],[10,7],[9,2],[7,-2],[5,-5],[3,-7]] },
    '*': { width: 16, points: [[8,21],[8,9],null,[3,18],[13,12],null,[13,18],[3,12]] },
    '+': { width: 26, points: [[13,18],[13,0],null,[4,9],[22,9]] },
    ',': { width: 10, points: [[6,1],[5,0],[4,1],[5,2],[6,1],[6,-1],[5,-3],[4,-4]] },
    '-': { width: 26, points: [[4,9],[22,9]] },
    '.': { width: 10, points: [[5,2],[4,1],[5,0],[6,1],[5,2]] },
    '/': { width: 22, points: [[20,25],[2,-7]] },
    '0': { width: 20, points: [[9,21],[6,20],[4,17],[3,12],[3,9],[4,4],[6,1],[9,0],[11,0],[14,1],[16,4],[17,9],[17,12],[16,17],[14,20],[11,21],[9,21]] },
    '1': { width: 20, points: [[6,17],[8,18],[11,21],[11,0]] },
    '2': { width: 20, points: [[4,16],[4,17],[5,19],[6,20],[8,21],[12,21],[14,20],[15,19],[16,17],[16,15],[15,13],[13,10],[3,0],[17,0]] },
    '3': { width: 20, points: [[5,21],[16,21],[10,13],[13,13],[15,12],[16,11],[17,8],[17,6],[16,3],[14,1],[11,0],[8,0],[5,1],[4,2],[3,4]] },
    '4': { width: 20, points: [[13,21],[3,7],[18,7],null,[13,21],[13,0]] },
    '5': { width: 20, points: [[15,21],[5,21],[4,12],[5,13],[8,14],[11,14],[14,13],[16,11],[17,8],[17,6],[16,3],[14,1],[11,0],[8,0],[5,1],[4,2],[3,4]] },
    '6': { width: 20, points: [[16,18],[15,20],[12,21],[10,21],[7,20],[5,17],[4,12],[4,7],[5,3],[7,1],[10,0],[11,0],[14,1],[16,3],[17,6],[17,7],[16,10],[14,12],[11,13],[10,13],[7,12],[5,10],[4,7]] },
    '7': { width: 20, points: [[17,21],[7,0],null,[3,21],[17,21]] },
    '8': { width: 20, points: [[8,21],[5,20],[4,18],[4,16],[5,14],[7,13],[11,12],[14,11],[16,9],[17,7],[17,4],[16,2],[15,1],[12,0],[8,0],[5,1],[4,2],[3,4],[3,7],[4,9],[6,11],[9,12],[13,13],[15,14],[16,16],[16,18],[15,20],[12,21],[8,21]] },
    '9': { width: 20, points: [[16,14],[15,11],[13,9],[10,8],[9,8],[6,9],[4,11],[3,14],[3,15],[4,18],[6,20],[9,21],[10,21],[13,20],[15,18],[16,14],[16,9],[15,4],[13,1],[10,0],[8,0],[5,1],[4,3]] },
    ':': { width: 10, points: [[5,14],[4,13],[5,12],[6,13],[5,14],null,[5,2],[4,1],[5,0],[6,1],[5,2]] },
    ';': { width: 10, points: [[5,14],[4,13],[5,12],[6,13],[5,14],null,[6,1],[5,0],[4,1],[5,2],[6,1],[6,-1],[5,-3],[4,-4]] },
    '<': { width: 24, points: [[20,18],[4,9],[20,0]] },
    '=': { width: 26, points: [[4,12],[22,12],null,[4,6],[22,6]] },
    '>': { width: 24, points: [[4,18],[20,9],[4,0]] },
    '?': { width: 18, points: [[3,16],[3,17],[4,19],[5,20],[7,21],[11,21],[13,20],[14,19],[15,17],[15,15],[14,13],[13,12],[9,10],[9,7],null,[9,2],[8,1],[9,0],[10,1],[9,2]] },
    '@': { width: 27, points: [[18,13],[17,15],[15,16],[12,16],[10,15],[9,14],[8,11],[8,8],[9,6],[11,5],[14,5],[16,6],[17,8],null,[12,16],[10,14],[9,11],[9,8],[10,6],[11,5],null,[18,16],[17,8],[17,6],[19,5],[21,5],[23,7],[24,10],[24,12],[23,15],[22,17],[20,19],[18,20],[15,21],[12,21],[9,20],[7,19],[5,17],[4,15],[3,12],[3,9],[4,6],[5,4],[7,2],[9,1],[12,0],[15,0],[18,1],[20,2],[21,3],null,[19,16],[18,8],[18,6],[19,5]] },
    'A': { width: 18, points: [[9,21],[1,0],null,[9,21],[17,0],null,[4,7],[14,7]] },
    'B': { width: 21, points: [[4,21],[4,0],null,[4,21],[13,21],[16,20],[17,19],[18,17],[18,15],[17,13],[16,12],[13,11],null,[4,11],[13,11],[16,10],[17,9],[18,7],[18,4],[17,2],[16,1],[13,0],[4,0]] },
    'C': { width: 21, points: [[18,16],[17,18],[15,20],[13,21],[9,21],[7,20],[5,18],[4,16],[3,13],[3,8],[4,5],[5,3],[7,1],[9,0],[13,0],[15,1],[17,3],[18,5]] },
    'D': { width: 21, points: [[4,21],[4,0],null,[4,21],[11,21],[14,20],[16,18],[17,16],[18,13],[18,8],[17,5],[16,3],[14,1],[11,0],[4,0]] },
    'E': { width: 19, points: [[4,21],[4,0],null,[4,21],[17,21],null,[4,11],[12,11],null,[4,0],[17,0]] },
    'F': { width: 18, points: [[4,21],[4,0],null,[4,21],[17,21],null,[4,11],[12,11]] },
    'G': { width: 21, points: [[18,16],[17,18],[15,20],[13,21],[9,21],[7,20],[5,18],[4,16],[3,13],[3,8],[4,5],[5,3],[7,1],[9,0],[13,0],[15,1],[17,3],[18,5],[18,8],null,[13,8],[18,8]] },
    'H': { width: 22, points: [[4,21],[4,0],null,[18,21],[18,0],null,[4,11],[18,11]] },
    'I': { width: 8,  points: [[4,21],[4,0]] },
    'J': { width: 16, points: [[12,21],[12,5],[11,2],[10,1],[8,0],[6,0],[4,1],[3,2],[2,5],[2,7]] },
    'K': { width: 21, points: [[4,21],[4,0],null,[18,21],[4,7],null,[9,12],[18,0]] },
    'L': { width: 17, points: [[4,21],[4,0],null,[4,0],[16,0]] },
    'M': { width: 24, points: [[4,21],[4,0],null,[4,21],[12,0],null,[20,21],[12,0],null,[20,21],[20,0]] },
    'N': { width: 22, points: [[4,21],[4,0],null,[4,21],[18,0],null,[18,21],[18,0]] },
    'O': { width: 22, points: [[9,21],[7,20],[5,18],[4,16],[3,13],[3,8],[4,5],[5,3],[7,1],[9,0],[13,0],[15,1],[17,3],[18,5],[19,8],[19,13],[18,16],[17,18],[15,20],[13,21],[9,21]] },
    'P': { width: 21, points: [[4,21],[4,0],null,[4,21],[13,21],[16,20],[17,19],[18,17],[18,14],[17,12],[16,11],[13,10],[4,10]] },
    'Q': { width: 22, points: [[9,21],[7,20],[5,18],[4,16],[3,13],[3,8],[4,5],[5,3],[7,1],[9,0],[13,0],[15,1],[17,3],[18,5],[19,8],[19,13],[18,16],[17,18],[15,20],[13,21],[9,21],null,[12,4],[18,-2]] },
    'R': { width: 21, points: [[4,21],[4,0],null,[4,21],[13,21],[16,20],[17,19],[18,17],[18,15],[17,13],[16,12],[13,11],[4,11],null,[11,11],[18,0]] },
    'S': { width: 20, points: [[17,18],[15,20],[12,21],[8,21],[5,20],[3,18],[3,16],[4,14],[5,13],[7,12],[13,10],[15,9],[16,8],[17,6],[17,3],[15,1],[12,0],[8,0],[5,1],[3,3]] },
    'T': { width: 16, points: [[8,21],[8,0],null,[1,21],[15,21]] },
    'U': { width: 22, points: [[4,21],[4,6],[5,3],[7,1],[10,0],[12,0],[15,1],[17,3],[18,6],[18,21]] },
    'V': { width: 18, points: [[1,21],[9,0],null,[17,21],[9,0]] },
    'W': { width: 24, points: [[2,21],[7,0],null,[12,21],[7,0],null,[12,21],[17,0],null,[22,21],[17,0]] },
    'X': { width: 20, points: [[3,21],[17,0],null,[17,21],[3,0]] },
    'Y': { width: 18, points: [[1,21],[9,11],[9,0],null,[17,21],[9,11]] },
    'Z': { width: 20, points: [[17,21],[3,0],null,[3,21],[17,21],null,[3,0],[17,0]] },
    '[': { width: 14, points: [[4,25],[4,-7],null,[5,25],[5,-7],null,[4,25],[11,25],null,[4,-7],[11,-7]] },
    '\\':{ width: 14, points: [[0,21],[14,-3]] },
    ']': { width: 14, points: [[9,25],[9,-7],null,[10,25],[10,-7],null,[3,25],[10,25],null,[3,-7],[10,-7]] },
    '^': { width: 14, points: [[3,10],[8,18],[13,10]] },
    '_': { width: 16, points: [[0,-2],[16,-2]] },
    '`': { width: 10, points: [[6,21],[5,20],[4,18],[4,16],[5,15],[6,16],[5,17]] },
    'a': { width: 19, points: [[15,14],[15,0],null,[15,11],[13,13],[11,14],[8,14],[6,13],[4,11],[3,8],[3,6],[4,3],[6,1],[8,0],[11,0],[13,1],[15,3]] },
    'b': { width: 19, points: [[4,21],[4,0],null,[4,11],[6,13],[8,14],[11,14],[13,13],[15,11],[16,8],[16,6],[15,3],[13,1],[11,0],[8,0],[6,1],[4,3]] },
    'c': { width: 18, points: [[15,11],[13,13],[11,14],[8,14],[6,13],[4,11],[3,8],[3,6],[4,3],[6,1],[8,0],[11,0],[13,1],[15,3]] },
    'd': { width: 19, points: [[15,21],[15,0],null,[15,11],[13,13],[11,14],[8,14],[6,13],[4,11],[3,8],[3,6],[4,3],[6,1],[8,0],[11,0],[13,1],[15,3]] },
    'e': { width: 18, points: [[3,8],[15,8],[15,10],[14,12],[13,13],[11,14],[8,14],[6,13],[4,11],[3,8],[3,6],[4,3],[6,1],[8,0],[11,0],[13,1],[15,3]] },
    'f': { width: 12, points: [[10,21],[8,21],[6,20],[5,17],[5,0],null,[2,14],[9,14]] },
    'g': { width: 19, points: [[15,14],[15,-2],[14,-5],[13,-6],[11,-7],[8,-7],[6,-6],null,[15,11],[13,13],[11,14],[8,14],[6,13],[4,11],[3,8],[3,6],[4,3],[6,1],[8,0],[11,0],[13,1],[15,3]] },
    'h': { width: 19, points: [[4,21],[4,0],null,[4,10],[7,13],[9,14],[12,14],[14,13],[15,10],[15,0]] },
    'i': { width: 8,  points: [[3,21],[4,20],[5,21],[4,22],[3,21],null,[4,14],[4,0]] },
    'j': { width: 10, points: [[5,21],[6,20],[7,21],[6,22],[5,21],null,[6,14],[6,-3],[5,-6],[3,-7],[1,-7]] },
    'k': { width: 17, points: [[4,21],[4,0],null,[14,14],[4,4],null,[8,8],[15,0]] },
    'l': { width: 8,  points: [[4,21],[4,0]] },
    'm': { width: 30, points: [[4,14],[4,0],null,[4,10],[7,13],[9,14],[12,14],[14,13],[15,10],[15,0],null,[15,10],[18,13],[20,14],[23,14],[25,13],[26,10],[26,0]] },
    'n': { width: 19, points: [[4,14],[4,0],null,[4,10],[7,13],[9,14],[12,14],[14,13],[15,10],[15,0]] },
    'o': { width: 19, points: [[8,14],[6,13],[4,11],[3,8],[3,6],[4,3],[6,1],[8,0],[11,0],[13,1],[15,3],[16,6],[16,8],[15,11],[13,13],[11,14],[8,14]] },
    'p': { width: 19, points: [[4,14],[4,-7],null,[4,11],[6,13],[8,14],[11,14],[13,13],[15,11],[16,8],[16,6],[15,3],[13,1],[11,0],[8,0],[6,1],[4,3]] },
    'q': { width: 19, points: [[15,14],[15,-7],null,[15,11],[13,13],[11,14],[8,14],[6,13],[4,11],[3,8],[3,6],[4,3],[6,1],[8,0],[11,0],[13,1],[15,3]] },
    'r': { width: 13, points: [[4,14],[4,0],null,[4,8],[5,11],[7,13],[9,14],[12,14]] },
    's': { width: 17, points: [[14,11],[13,13],[10,14],[7,14],[4,13],[3,11],[4,9],[6,8],[11,7],[13,6],[14,4],[14,3],[13,1],[10,0],[7,0],[4,1],[3,3]] },
    't': { width: 12, points: [[5,21],[5,4],[6,1],[8,0],[10,0],null,[2,14],[9,14]] },
    'u': { width: 19, points: [[4,14],[4,4],[5,1],[7,0],[10,0],[12,1],[15,4],null,[15,14],[15,0]] },
    'v': { width: 16, points: [[2,14],[8,0],null,[14,14],[8,0]] },
    'w': { width: 22, points: [[3,14],[7,0],null,[11,14],[7,0],null,[11,14],[15,0],null,[19,14],[15,0]] },
    'x': { width: 17, points: [[3,14],[14,0],null,[14,14],[3,0]] },
    'y': { width: 16, points: [[2,14],[8,0],null,[14,14],[8,0],[6,-4],[4,-6],[2,-7],[1,-7]] },
    'z': { width: 17, points: [[14,14],[3,0],null,[3,14],[14,14],null,[3,0],[14,0]] },
    '{': { width: 14, points: [[9,25],[7,24],[6,23],[5,21],[5,19],[6,17],[7,16],[8,14],[8,12],[6,10],null,[7,24],[6,22],[6,20],[7,18],[8,17],[9,15],[9,13],[8,11],[4,9],[8,7],[9,5],[9,3],[8,1],[7,0],[6,-2],[6,-4],[7,-6],null,[6,8],[8,6],[8,4],[7,2],[6,1],[5,-1],[5,-3],[6,-5],[7,-6],[9,-7]] },
    '|': { width: 8,  points: [[4,25],[4,-7]] },
    '}': { width: 14, points: [[5,25],[7,24],[8,23],[9,21],[9,19],[8,17],[7,16],[6,14],[6,12],[8,10],null,[7,24],[8,22],[8,20],[7,18],[6,17],[5,15],[5,13],[6,11],[10,9],[6,7],[5,5],[5,3],[6,1],[7,0],[8,-2],[8,-4],[7,-6],null,[8,8],[6,6],[6,4],[7,2],[8,1],[9,-1],[9,-3],[8,-5],[7,-6],[5,-7]] },
    '~': { width: 24, points: [[3,6],[3,8],[4,11],[6,12],[8,12],[10,11],[14,8],[16,7],[18,7],[20,8],[21,10],null,[3,8],[4,10],[6,11],[8,11],[10,10],[14,7],[16,6],[18,6],[20,7],[21,10],[21,12]] },
    
    // Lower case Latin-1
    'à': { diacritic: '`', letter: 'a' },
    'á': { diacritic: '´', letter: 'a' },
    'â': { diacritic: '^', letter: 'a' },
    'ä': { diacritic: '¨', letter: 'a' },
    'ã': { diacritic: '~', letter: 'a' },
    
    'è': { diacritic: '`', letter: 'e' },
    'é': { diacritic: '´', letter: 'e' },
    'ê': { diacritic: '^', letter: 'e' },
    'ë': { diacritic: '¨', letter: 'e' },
    
    'ì': { diacritic: '`', letter: 'i' },
    'í': { diacritic: '´', letter: 'i' },
    'î': { diacritic: '^', letter: 'i' },
    'ï': { diacritic: '¨', letter: 'i' },
    
    'ò': { diacritic: '`', letter: 'o' },
    'ó': { diacritic: '´', letter: 'o' },
    'ô': { diacritic: '^', letter: 'o' },
    'ö': { diacritic: '¨', letter: 'o' },
    'õ': { diacritic: '~', letter: 'o' },

    'ù': { diacritic: '`', letter: 'u' },
    'ú': { diacritic: '´', letter: 'u' },
    'û': { diacritic: '^', letter: 'u' },
    'ü': { diacritic: '¨', letter: 'u' },
    
    'ý': { diacritic: '´', letter: 'y' },
    'ÿ': { diacritic: '¨', letter: 'y' },
    
    'ç': { diacritic: '¸', letter: 'c' },
    'ñ': { diacritic: '~', letter: 'n' },

    // Upper case Latin-1
    'À': { diacritic: '`', letter: 'A' },
    'Á': { diacritic: '´', letter: 'A' },
    'Â': { diacritic: '^', letter: 'A' },
    'Ä': { diacritic: '¨', letter: 'A' },
    'Ã': { diacritic: '~', letter: 'A' },
    
    'È': { diacritic: '`', letter: 'E' },
    'É': { diacritic: '´', letter: 'E' },
    'Ê': { diacritic: '^', letter: 'E' },
    'Ë': { diacritic: '¨', letter: 'E' },

    'Ì': { diacritic: '`', letter: 'I' },
    'Í': { diacritic: '´', letter: 'I' },
    'Î': { diacritic: '^', letter: 'I' },
    'Ï': { diacritic: '¨', letter: 'I' },
    
    'Ò': { diacritic: '`', letter: 'O' },
    'Ó': { diacritic: '´', letter: 'O' },
    'Ô': { diacritic: '^', letter: 'O' },
    'Ö': { diacritic: '¨', letter: 'O' },
    'Õ': { diacritic: '~', letter: 'O' },
    
    'Ù': { diacritic: '`', letter: 'U' },
    'Ú': { diacritic: '´', letter: 'U' },
    'Û': { diacritic: '^', letter: 'U' },
    'Ü': { diacritic: '¨', letter: 'U' },
    
    'Ý': { diacritic: '´', letter: 'Y' },
    
    'Ç': { diacritic: '¸', letter: 'C' },
    'Ñ': { diacritic: '~', letter: 'N' }
  },
  
  specialchars: {
    'pi': { width: 19, points: [[6,14],[6,0],null,[14,14],[14,0],null,[2,13],[6,16],[13,13],[17,16]] }
  },
  
  /** Diacritics, used to draw accentuated letters */
  diacritics: {
    '¸': { entity: 'cedil', points: [[6,-4],[4,-6],[2,-7],[1,-7]] },
    '´': { entity: 'acute', points: [[8,19],[13,22]] },
    '`': { entity: 'grave', points: [[7,22],[12,19]] },
    '^': { entity: 'circ',  points: [[5.5,19],[9.5,23],[12.5,19]] },
    '¨': { entity: 'trema', points: [[5,21],[6,20],[7,21],[6,22],[5,21],null,[12,21],[13,20],[14,21],[13,22],[12,21]] },
    '~': { entity: 'tilde', points: [[4,18],[7,22],[10,18],[13,22]] }
  },
  
  /** The default font styling */
  style: {
    size: 8,            // font height in pixels
    font: null,         // not yet implemented
    color: '#000000',   // font color
    weight: 1,          // float, 1 for 'normal'
    textAlign: 'left',  // left, right, center
    textBaseline: 'bottom', // top, middle, bottom 
    adjustAlign: false, // modifies the alignments if the angle is different from 0 to make the spin point always at the good position
    angle: 0,           // in radians, anticlockwise
    tracking: 1,        // space between the letters, float, 1 for 'normal'
    boundingBoxColor: '#ff0000', // color of the bounding box (null to hide), can be used for debug and font drawing
    originPointColor: '#000000'  // color of the bounding box (null to hide), can be used for debug and font drawing
  },
  
  debug: false,
  _bufferLexemes: {},

  extend: function(dest, src) {
    for (var property in src) {
      if (property in dest) continue;
      dest[property] = src[property];
    }
    return dest;
  },

  /** Get the letter data corresponding to a char
   * @param {String} ch - The char
   */
  letter: function(ch) {
    return CanvasText.letters[ch];
  },
  
  parseLexemes: function(str) {
    if (CanvasText._bufferLexemes[str]) 
      return CanvasText._bufferLexemes[str];
    
    var i, c, matches = str.match(/&[A-Za-z]{2,5};|\s|./g),
        result = [], chars = [];
        
    for (i = 0; i < matches.length; i++) {
      c = matches[i];
      if (c.length == 1) 
        chars.push(c);
      else {
        var entity = c.substring(1, c.length-1);
        if (CanvasText.specialchars[entity]) 
          chars.push(entity);
        else
          chars = chars.concat(c.toArray());
      }
    }
    for (i = 0; i < chars.length; i++) {
      c = chars[i];
      if (c = CanvasText.letters[c] || CanvasText.specialchars[c]) result.push(c);
    }
    for (i = 0; i < result.length; i++) {
      if (result === null || typeof result === 'undefined') 
      delete result[i];
    }
    return CanvasText._bufferLexemes[str] = result;
  },

  /** Get the font ascent for a given style
   * @param {Object} style - The reference style
   */
  ascent: function(style) {
    style = style || CanvasText.style;
    return (style.size || CanvasText.style.size);
  },
  
  /** Get the font descent for a given style 
   * @param {Object} style - The reference style
   * */
  descent: function(style) {
    style = style || CanvasText.style;
    return 7.0*(style.size || CanvasText.style.size)/25.0;
  },
  
  /** Measure the text horizontal size 
   * @param {String} str - The text
   * @param {Object} style - Text style
   * */
  measure: function(str, style) {
    if (!str) return;
    style = style || CanvasText.style;
    
    var i, width, lexemes = CanvasText.parseLexemes(str),
        total = 0;

    for (i = lexemes.length-1; i > -1; --i) {
      c = lexemes[i];
      width = (c.diacritic) ? CanvasText.letter(c.letter).width : c.width;
      total += width * (style.tracking || CanvasText.style.tracking) * (style.size || CanvasText.style.size) / 25.0;
    }
    return total;
  },
  
  getDimensions: function(str, style) {
    style = style || CanvasText.style;
    
    var width = CanvasText.measure(str, style),
        height = style.size || CanvasText.style.size,
        angle = style.angle || CanvasText.style.angle;

    if (style.angle == 0) return {width: width, height: height};
    return {
      width:  Math.abs(Math.cos(angle) * width) + Math.abs(Math.sin(angle) * height),
      height: Math.abs(Math.sin(angle) * width) + Math.abs(Math.cos(angle) * height)
    }
  },
  
  /** Draws serie of points at given coordinates 
   * @param {Canvas context} ctx - The canvas context
   * @param {Array} points - The points to draw
   * @param {Number} x - The X coordinate
   * @param {Number} y - The Y coordinate
   * @param {Number} mag - The scale 
   */
  drawPoints: function (ctx, points, x, y, mag, offset) {
    var i, a, penUp = true, needStroke = 0;
    offset = offset || {x:0, y:0};
    
    ctx.beginPath();
    for (i = 0; i < points.length; i++) {
      a = points[i];
      if (!a) {
        penUp = true;
        continue;
      }
      if (penUp) {
        ctx.moveTo(x + a[0]*mag + offset.x, y - a[1]*mag + offset.y);
        penUp = false;
      }
      else {
        ctx.lineTo(x + a[0]*mag + offset.x, y - a[1]*mag + offset.y);
      }
    }
    ctx.stroke();
    ctx.closePath();
  },
  
  /** Draws a text at given coordinates and with a given style
   * @param {String} str - The text to draw
   * @param {Number} xOrig - The X coordinate
   * @param {Number} yOrig - The Y coordinate
   * @param {Object} style - The font style
   */
  draw: function(str, xOrig, yOrig, style) {
    if (!str) return;
    CanvasText.extend(style, CanvasText.style);
    
    var i, c, total = 0,
        mag = style.size / 25.0,
        x = 0, y = 0,
        lexemes = CanvasText.parseLexemes(str),
        offset = {x: 0, y: 0}, 
        measure = CanvasText.measure(str, style),
        align;
        
    if (style.adjustAlign) {
      align = CanvasText.getBestAlign(style.angle, style);
      CanvasText.extend(style, align);
    }
        
    switch (style.textAlign) {
      case 'left': break;
      case 'center': offset.x = -measure / 2; break;
      case 'right':  offset.x = -measure; break;
    }
    
    switch (style.textBaseline) {
      case 'bottom': break;
      case 'middle': offset.y = style.size / 2; break;
      case 'top':    offset.y = style.size; break;
    }
    
    this.save();
    this.translate(xOrig, yOrig);
    this.rotate(style.angle);
    this.lineCap = "round";
    this.lineWidth = 2.0 * mag * (style.weight || CanvasText.style.weight);
    this.strokeStyle = style.color || CanvasText.style.color;
    
    for (i = 0; i < lexemes.length; i++) {
      c = lexemes[i];
      if (c.width == -1) {
        x = 0;
        y = style.size * 1.4;
        continue;
      }
    
      var points = c.points,
          width = c.width;
          
      if (c.diacritic) {
        var dia = CanvasText.diacritics[c.diacritic],
            character = CanvasText.letter(c.letter);

        CanvasText.drawPoints(this, dia.points, x, y - (c.letter.toUpperCase() == c.letter ? 3 : 0), mag, offset);
        points = character.points;
        width = character.width;
      }

      CanvasText.drawPoints(this, points, x, y, mag, offset);
      
      if (CanvasText.debug) {
        this.save();
        this.lineJoin = "miter";
        this.lineWidth = 0.5;
        this.strokeStyle = (style.boundingBoxColor || CanvasText.style.boundingBoxColor);
        this.strokeRect(x+offset.x, y+offset.y, width*mag, -style.size);
        
        this.fillStyle = (style.originPointColor || CanvasText.style.originPointColor);
        this.beginPath();
        this.arc(0, 0, 1.5, 0, Math.PI*2, true);
        this.fill();
        this.closePath();
        this.restore();
      }
      
      x += width*mag*(style.tracking || CanvasText.style.tracking);
    }
    this.restore();
    return total;
  }
};

/** The text functions are bound to the CanvasRenderingContext2D prototype */
CanvasText.proto = window.CanvasRenderingContext2D ? window.CanvasRenderingContext2D.prototype : document.createElement('canvas').getContext('2d').__proto__;

if (CanvasText.proto) {
  CanvasText.proto.drawText      = CanvasText.draw;
  CanvasText.proto.measure       = CanvasText.measure;
  CanvasText.proto.getTextBounds = CanvasText.getDimensions;
  CanvasText.proto.fontAscent    = CanvasText.ascent;
  CanvasText.proto.fontDescent   = CanvasText.descent;
}