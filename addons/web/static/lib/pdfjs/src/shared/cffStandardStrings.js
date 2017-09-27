/* -*- Mode: Java; tab-width: 2; indent-tabs-mode: nil; c-basic-offset: 2 -*- */
/* vim: set shiftwidth=2 tabstop=2 autoindent cindent expandtab: */
/* Copyright 2012 Mozilla Foundation
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

'use strict';

var CFFEncodingMap = {
  '0': '-reserved-',
  '1': 'hstem',
  '2': '-reserved-',
  '3': 'vstem',
  '4': 'vmoveto',
  '5': 'rlineto',
  '6': 'hlineto',
  '7': 'vlineto',
  '8': 'rrcurveto',
  '9': '-reserved-',
  '10': 'callsubr',
  '11': 'return',
  '12': {
    '3': 'and',
    '4': 'or',
    '5': 'not',
    '9': 'abs',
    '10': 'add',
    '11': 'div',
    '12': 'sub',
    '14': 'neg',
    '15': 'eq',
    '18': 'drop',
    '20': 'put',
    '21': 'get',
    '22': 'ifelse',
    '23': 'random',
    '24': 'mul',
    '26': 'sqrt',
    '27': 'dup',
    '28': 'exch',
    '29': 'index',
    '30': 'roll',
    '34': 'hflex',
    '35': 'flex',
    '36': 'hflex1',
    '37': 'flex1'
  },
  '13': '-reserved-',
  '14': 'endchar',
  '15': '-reserved-',
  '16': '-reserved-',
  '17': '-reserved-',
  '18': 'hstemhm',
  '19': 'hintmask',
  '20': 'cntrmask',
  '21': 'rmoveto',
  '22': 'hmoveto',
  '23': 'vstemhm',
  '24': 'rcurveline',
  '25': 'rlivecurve',
  '26': 'vvcurveto',
  '27': 'hhcurveto',
  '29': 'callgsubr',
  '30': 'vhcurveto',
  '31': 'hvcurveto'
};

var CFFDictDataMap = {
  '0': {
    name: 'version',
    operand: 'SID'
  },
  '1': {
    name: 'Notice',
    operand: 'SID'
  },
  '2': {
    name: 'FullName',
    operand: 'SID'
  },
  '3': {
    name: 'FamilyName',
    operand: 'SID'
  },
  '4': {
    name: 'Weight',
    operand: 'SID'
  },
  '5': {
    name: 'FontBBox',
    operand: [0, 0, 0, 0]
  },
  '6': {
    name: 'BlueValues'
  },
  '7': {
    name: 'OtherBlues'
  },
  '8': {
    name: 'FamilyBlues'
  },
  '9': {
    name: 'FamilyOtherBlues'
  },
  '10': {
    name: 'StdHW'
  },
  '11': {
    name: 'StdVW'
  },
  '12': {
    '0': {
      name: 'Copyright',
      operand: 'SID'
    },
    '1': {
      name: 'IsFixedPitch',
      operand: false
    },
    '2': {
      name: 'ItalicAngle',
      operand: 0
    },
    '3': {
      name: 'UnderlinePosition',
      operand: -100
    },
    '4': {
      name: 'UnderlineThickness',
      operand: 50
    },
    '5': {
      name: 'PaintType',
      operand: 0
    },
    '6': {
      name: 'CharstringType',
      operand: 2
    },
    '7': {
      name: 'FontMatrix',
      operand: [0.001, 0, 0, 0.001, 0 , 0]
    },
    '8': {
      name: 'StrokeWidth',
      operand: 0
    },
    '9': {
      name: 'BlueScale'
    },
    '10': {
      name: 'BlueShift'
    },
    '11': {
      name: 'BlueFuzz'
    },
    '12': {
      name: 'StemSnapH'
    },
    '13': {
      name: 'StemSnapV'
    },
    '14': {
      name: 'ForceBold'
    },
    '17': {
      name: 'LanguageGroup'
    },
    '18': {
      name: 'ExpansionFactor'
    },
    '19': {
      name: 'initialRandomSeed'
    },
    '20': {
      name: 'SyntheticBase',
      operand: null
    },
    '21': {
      name: 'PostScript',
      operand: 'SID'
    },
    '22': {
      name: 'BaseFontName',
      operand: 'SID'
    },
    '23': {
      name: 'BaseFontBlend',
      operand: 'delta'
    }
  },
  '13': {
    name: 'UniqueID',
    operand: null
  },
  '14': {
    name: 'XUID',
    operand: []
  },
  '15': {
    name: 'charset',
    operand: 0
  },
  '16': {
    name: 'Encoding',
    operand: 0
  },
  '17': {
    name: 'CharStrings',
    operand: null
  },
  '18': {
    name: 'Private',
    operand: 'number number'
  },
  '19': {
    name: 'Subrs'
  },
  '20': {
    name: 'defaultWidthX'
  },
  '21': {
    name: 'nominalWidthX'
  }
};

var CFFDictPrivateDataMap = {
  '6': {
    name: 'BluesValues',
    operand: 'delta'
  },
  '7': {
    name: 'OtherBlues',
    operand: 'delta'
  },
  '8': {
    name: 'FamilyBlues',
    operand: 'delta'
  },
  '9': {
    name: 'FamilyOtherBlues',
    operand: 'delta'
  },
  '10': {
    name: 'StdHW',
    operand: null
  },
  '11': {
    name: 'StdVW',
    operand: null
  },
  '12': {
    '9': {
      name: 'BlueScale',
      operand: 0.039625
    },
    '10': {
      name: 'BlueShift',
      operand: 7
    },
    '11': {
      name: 'BlueFuzz',
      operand: 1
    },
    '12': {
      name: 'StemSnapH',
      operand: 'delta'
    },
    '13': {
      name: 'StemSnapV',
      operand: 'delta'
    },
    '14': {
      name: 'ForceBold',
      operand: 'boolean'
    },
    '17': {
      name: 'LanguageGroup',
      operand: 0
    },
    '18': {
      name: 'ExpansionFactor',
      operand: 0.06
    },
    '19': {
      name: 'initialRandomSeed',
      operand: 0
    }
  },
  '19': {
    name: 'Subrs',
    operand: null
  },
  '20': {
    name: 'defaultWidthX',
    operand: 0
  },
  '21': {
    name: 'nominalWidthX',
    operand: 0
  }
};
