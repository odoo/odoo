/* ***** BEGIN LICENSE BLOCK *****
 * Distributed under the BSD license:
 *
 * Copyright (c) 2010, Ajax.org B.V.
 * All rights reserved.
 * 
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *     * Redistributions of source code must retain the above copyright
 *       notice, this list of conditions and the following disclaimer.
 *     * Redistributions in binary form must reproduce the above copyright
 *       notice, this list of conditions and the following disclaimer in the
 *       documentation and/or other materials provided with the distribution.
 *     * Neither the name of Ajax.org B.V. nor the
 *       names of its contributors may be used to endorse or promote products
 *       derived from this software without specific prior written permission.
 * 
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
 * ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
 * WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL AJAX.ORG B.V. BE LIABLE FOR ANY
 * DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
 * (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 * LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 * ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
 * SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 *
 * ***** END LICENSE BLOCK ***** */

define(function(require, exports, module) {
"use strict";

var oop = require("../lib/oop");
var c_cppHighlightRules = require("./c_cpp_highlight_rules").c_cppHighlightRules;

var glslHighlightRules = function() {

    var keywords = (
        "attribute|const|uniform|varying|break|continue|do|for|while|" +
        "if|else|in|out|inout|float|int|void|bool|true|false|" +
        "lowp|mediump|highp|precision|invariant|discard|return|mat2|mat3|" +
        "mat4|vec2|vec3|vec4|ivec2|ivec3|ivec4|bvec2|bvec3|bvec4|sampler2D|" +
        "samplerCube|struct"
    );

    var buildinConstants = (
        "radians|degrees|sin|cos|tan|asin|acos|atan|pow|" +
        "exp|log|exp2|log2|sqrt|inversesqrt|abs|sign|floor|ceil|fract|mod|" +
        "min|max|clamp|mix|step|smoothstep|length|distance|dot|cross|" +
        "normalize|faceforward|reflect|refract|matrixCompMult|lessThan|" +
        "lessThanEqual|greaterThan|greaterThanEqual|equal|notEqual|any|all|" +
        "not|dFdx|dFdy|fwidth|texture2D|texture2DProj|texture2DLod|" +
        "texture2DProjLod|textureCube|textureCubeLod|" +
        "gl_MaxVertexAttribs|gl_MaxVertexUniformVectors|gl_MaxVaryingVectors|" +
        "gl_MaxVertexTextureImageUnits|gl_MaxCombinedTextureImageUnits|" +
        "gl_MaxTextureImageUnits|gl_MaxFragmentUniformVectors|gl_MaxDrawBuffers|" +
        "gl_DepthRangeParameters|gl_DepthRange|" +
        // The following two are only for MIME x-shader/x-vertex.
        "gl_Position|gl_PointSize|" +
        // The following five are only for MIME x-shader/x-fragment.
        "gl_FragCoord|gl_FrontFacing|gl_PointCoord|gl_FragColor|gl_FragData"
    );

    var keywordMapper = this.createKeywordMapper({
        "variable.language": "this",
        "keyword": keywords,
        "constant.language": buildinConstants
    }, "identifier");

    this.$rules = new c_cppHighlightRules().$rules;
    this.$rules.start.forEach(function(rule) {
        if (typeof rule.token == "function")
            rule.token = keywordMapper;
    })
};

oop.inherits(glslHighlightRules, c_cppHighlightRules);

exports.glslHighlightRules = glslHighlightRules;
});
