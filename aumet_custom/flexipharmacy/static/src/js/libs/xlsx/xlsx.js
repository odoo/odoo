/* xlsx.js (C) 2013-present SheetJS -- http://sheetjs.com */
/* vim: set ts=2: */
/*jshint -W041 */
/*jshint funcscope:true, eqnull:true, loopfunc:true */
/*exported XLSX */
/*global global, exports, module, require:false, process:false, Buffer:false */
var XLSX = {};
(function make_xlsx(XLSX){
XLSX.version = '0.10.3';
var current_codepage = 1200;
/*global cptable:true */
if(typeof module !== "undefined" && typeof require !== 'undefined') {
	if(typeof cptable === 'undefined') global.cptable = require('./dist/cpexcel.js');
}
function reset_cp() { set_cp(1200); }
var set_cp = function(cp) { current_codepage = cp; };

function char_codes(data) { var o = []; for(var i = 0, len = data.length; i < len; ++i) o[i] = data.charCodeAt(i); return o; }
var debom = function(data) {
	var c1 = data.charCodeAt(0), c2 = data.charCodeAt(1);
	if(c1 == 0xFF && c2 == 0xFE) return data.substr(2);
	if(c1 == 0xFE && c2 == 0xFF) return data.substr(2);
	if(c1 == 0xFEFF) return data.substr(1);
	return data;
};

var _getchar = function _gc1(x) { return String.fromCharCode(x); };
if(typeof cptable !== 'undefined') {
	set_cp = function(cp) { current_codepage = cp; };
	debom = function(data) {
		if(data.charCodeAt(0) === 0xFF && data.charCodeAt(1) === 0xFE) { return cptable.utils.decode(1200, char_codes(data.substr(2))); }
		return data;
	};
	_getchar = function _gc2(x) {
		if(current_codepage === 1200) return String.fromCharCode(x);
		return cptable.utils.decode(current_codepage, [x&255,x>>8])[0];
	};
}
var DENSE = null;
var DIF_XL = true;
var Base64 = (function make_b64(){
	var map = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=";
	return {
		encode: function(input) {
			var o = "";
			var c1, c2, c3, e1, e2, e3, e4;
			for(var i = 0; i < input.length; ) {
				c1 = input.charCodeAt(i++);
				c2 = input.charCodeAt(i++);
				c3 = input.charCodeAt(i++);
				e1 = c1 >> 2;
				e2 = (c1 & 3) << 4 | c2 >> 4;
				e3 = (c2 & 15) << 2 | c3 >> 6;
				e4 = c3 & 63;
				if (isNaN(c2)) { e3 = e4 = 64; }
				else if (isNaN(c3)) { e4 = 64; }
				o += map.charAt(e1) + map.charAt(e2) + map.charAt(e3) + map.charAt(e4);
			}
			return o;
		},
		decode: function b64_decode(input) {
			var o = "";
			var c1, c2, c3;
			var e1, e2, e3, e4;
			input = input.replace(/[^A-Za-z0-9\+\/\=]/g, "");
			for(var i = 0; i < input.length;) {
				e1 = map.indexOf(input.charAt(i++));
				e2 = map.indexOf(input.charAt(i++));
				e3 = map.indexOf(input.charAt(i++));
				e4 = map.indexOf(input.charAt(i++));
				c1 = e1 << 2 | e2 >> 4;
				c2 = (e2 & 15) << 4 | e3 >> 2;
				c3 = (e3 & 3) << 6 | e4;
				o += String.fromCharCode(c1);
				if (e3 != 64) { o += String.fromCharCode(c2); }
				if (e4 != 64) { o += String.fromCharCode(c3); }
			}
			return o;
		}
	};
})();
var has_buf = (typeof Buffer !== 'undefined' && typeof process !== 'undefined' && typeof process.versions !== 'undefined' && process.versions.node);

function new_raw_buf(len) {
	/* jshint -W056 */
	return new (has_buf ? Buffer : Array)(len);
	/* jshint +W056 */
}

function s2a(s) {
	if(has_buf) return new Buffer(s, "binary");
	return s.split("").map(function(x){ return x.charCodeAt(0) & 0xff; });
}

var bconcat = function(bufs) { return [].concat.apply([], bufs); };

var chr0 = /\u0000/g, chr1 = /[\u0001-\u0006]/;
/* ssf.js (C) 2013-present SheetJS -- http://sheetjs.com */
/*jshint -W041 */
var SSF = {};
var make_ssf = function make_ssf(SSF){
SSF.version = '0.9.3';
function _strrev(x) { var o = "", i = x.length-1; while(i>=0) o += x.charAt(i--); return o; }
function fill(c,l) { var o = ""; while(o.length < l) o+=c; return o; }
function pad0(v,d){var t=""+v; return t.length>=d?t:fill('0',d-t.length)+t;}
function pad_(v,d){var t=""+v;return t.length>=d?t:fill(' ',d-t.length)+t;}
function rpad_(v,d){var t=""+v; return t.length>=d?t:t+fill(' ',d-t.length);}
function pad0r1(v,d){var t=""+Math.round(v); return t.length>=d?t:fill('0',d-t.length)+t;}
function pad0r2(v,d){var t=""+v; return t.length>=d?t:fill('0',d-t.length)+t;}
var p2_32 = Math.pow(2,32);
function pad0r(v,d){if(v>p2_32||v<-p2_32) return pad0r1(v,d); var i = Math.round(v); return pad0r2(i,d); }
function isgeneral(s, i) { i = i || 0; return s.length >= 7 + i && (s.charCodeAt(i)|32) === 103 && (s.charCodeAt(i+1)|32) === 101 && (s.charCodeAt(i+2)|32) === 110 && (s.charCodeAt(i+3)|32) === 101 && (s.charCodeAt(i+4)|32) === 114 && (s.charCodeAt(i+5)|32) === 97 && (s.charCodeAt(i+6)|32) === 108; }
/* Options */
var opts_fmt = [
	["date1904", 0],
	["output", ""],
	["WTF", false]
];
function fixopts(o){
	for(var y = 0; y != opts_fmt.length; ++y) if(o[opts_fmt[y][0]]===undefined) o[opts_fmt[y][0]]=opts_fmt[y][1];
}
SSF.opts = opts_fmt;
var days = [
	['Sun', 'Sunday'],
	['Mon', 'Monday'],
	['Tue', 'Tuesday'],
	['Wed', 'Wednesday'],
	['Thu', 'Thursday'],
	['Fri', 'Friday'],
	['Sat', 'Saturday']
];
var months = [
	['J', 'Jan', 'January'],
	['F', 'Feb', 'February'],
	['M', 'Mar', 'March'],
	['A', 'Apr', 'April'],
	['M', 'May', 'May'],
	['J', 'Jun', 'June'],
	['J', 'Jul', 'July'],
	['A', 'Aug', 'August'],
	['S', 'Sep', 'September'],
	['O', 'Oct', 'October'],
	['N', 'Nov', 'November'],
	['D', 'Dec', 'December']
];
function init_table(t) {
	t[0]=  'General';
	t[1]=  '0';
	t[2]=  '0.00';
	t[3]=  '#,##0';
	t[4]=  '#,##0.00';
	t[9]=  '0%';
	t[10]= '0.00%';
	t[11]= '0.00E+00';
	t[12]= '# ?/?';
	t[13]= '# ??/??';
	t[14]= 'm/d/yy';
	t[15]= 'd-mmm-yy';
	t[16]= 'd-mmm';
	t[17]= 'mmm-yy';
	t[18]= 'h:mm AM/PM';
	t[19]= 'h:mm:ss AM/PM';
	t[20]= 'h:mm';
	t[21]= 'h:mm:ss';
	t[22]= 'm/d/yy h:mm';
	t[37]= '#,##0 ;(#,##0)';
	t[38]= '#,##0 ;[Red](#,##0)';
	t[39]= '#,##0.00;(#,##0.00)';
	t[40]= '#,##0.00;[Red](#,##0.00)';
	t[45]= 'mm:ss';
	t[46]= '[h]:mm:ss';
	t[47]= 'mmss.0';
	t[48]= '##0.0E+0';
	t[49]= '@';
	t[56]= '"上午/下午 "hh"時"mm"分"ss"秒 "';
	t[65535]= 'General';
}

var table_fmt = {};
init_table(table_fmt);
function frac(x, D, mixed) {
	var sgn = x < 0 ? -1 : 1;
	var B = x * sgn;
	var P_2 = 0, P_1 = 1, P = 0;
	var Q_2 = 1, Q_1 = 0, Q = 0;
	var A = Math.floor(B);
	while(Q_1 < D) {
		A = Math.floor(B);
		P = A * P_1 + P_2;
		Q = A * Q_1 + Q_2;
		if((B - A) < 0.00000005) break;
		B = 1 / (B - A);
		P_2 = P_1; P_1 = P;
		Q_2 = Q_1; Q_1 = Q;
	}
	if(Q > D) { if(Q_1 > D) { Q = Q_2; P = P_2; } else { Q = Q_1; P = P_1; } }
	if(!mixed) return [0, sgn * P, Q];
	var q = Math.floor(sgn * P/Q);
	return [q, sgn*P - q*Q, Q];
}
function general_fmt_int(v) { return ""+v; }
SSF._general_int = general_fmt_int;
var general_fmt_num = (function make_general_fmt_num() {
var gnr1 = /\.(\d*[1-9])0+$/, gnr2 = /\.0*$/, gnr4 = /\.(\d*[1-9])0+/, gnr5 = /\.0*[Ee]/, gnr6 = /(E[+-])(\d)$/;
function gfn2(v) {
	var w = (v<0?12:11);
	var o = gfn5(v.toFixed(12)); if(o.length <= w) return o;
	o = v.toPrecision(10); if(o.length <= w) return o;
	return v.toExponential(5);
}
function gfn3(v) {
	var o = v.toFixed(11).replace(gnr1,".$1");
	if(o.length > (v<0?12:11)) o = v.toPrecision(6);
	return o;
}
function gfn4(o) {
	for(var i = 0; i != o.length; ++i) if((o.charCodeAt(i) | 0x20) === 101) return o.replace(gnr4,".$1").replace(gnr5,"E").replace("e","E").replace(gnr6,"$10$2");
	return o;
}
function gfn5(o) {
	return o.indexOf(".") > -1 ? o.replace(gnr2,"").replace(gnr1,".$1") : o;
}
return function general_fmt_num(v) {
	var V = Math.floor(Math.log(Math.abs(v))*Math.LOG10E), o;
	if(V >= -4 && V <= -1) o = v.toPrecision(10+V);
	else if(Math.abs(V) <= 9) o = gfn2(v);
	else if(V === 10) o = v.toFixed(10).substr(0,12);
	else o = gfn3(v);
	return gfn5(gfn4(o));
};})();
SSF._general_num = general_fmt_num;
function general_fmt(v) {
	switch(typeof v) {
		case 'string': return v;
		case 'boolean': return v ? "TRUE" : "FALSE";
		case 'number': return (v|0) === v ? general_fmt_int(v/*, opts*/) : general_fmt_num(v/*, opts*/);
		case 'undefined': return "";
		case 'object': if(v == null) return "";
	}
	throw new Error("unsupported value in General format: " + v);
}
SSF._general = general_fmt;
function fix_hijri(/*date, o*/) { return 0; }
function parse_date_code(v,opts,b2) {
	if(v > 2958465 || v < 0) return null;
	var date = (v|0), time = Math.floor(86400 * (v - date)), dow=0;
	var dout=[];
	var out={D:date, T:time, u:86400*(v-date)-time,y:0,m:0,d:0,H:0,M:0,S:0,q:0};
	if(Math.abs(out.u) < 1e-6) out.u = 0;
	fixopts(opts != null ? opts : (opts=[]));
	if(opts.date1904) date += 1462;
	if(out.u > 0.9999) {
		out.u = 0;
		if(++time == 86400) { out.T = time = 0; ++date; ++out.D; }
	}
	if(date === 60) {dout = b2 ? [1317,10,29] : [1900,2,29]; dow=3;}
	else if(date === 0) {dout = b2 ? [1317,8,29] : [1900,1,0]; dow=6;}
	else {
		if(date > 60) --date;
		/* 1 = Jan 1 1900 in Gregorian */
		var d = new Date(1900, 0, 1);
		d.setDate(d.getDate() + date - 1);
		dout = [d.getFullYear(), d.getMonth()+1,d.getDate()];
		dow = d.getDay();
		if(date < 60) dow = (dow + 6) % 7;
		if(b2) dow = fix_hijri(d, dout);
	}
	out.y = dout[0]; out.m = dout[1]; out.d = dout[2];
	out.S = time % 60; time = Math.floor(time / 60);
	out.M = time % 60; time = Math.floor(time / 60);
	out.H = time;
	out.q = dow;
	return out;
}
SSF.parse_date_code = parse_date_code;
/*jshint -W086 */
function write_date(type, fmt, val, ss0) {
	var o="", ss=0, tt=0, y = val.y, out, outl = 0;
	switch(type) {
		case 98: /* 'b' buddhist year */
			y = val.y + 543;
			/* falls through */
		case 121: /* 'y' year */
		switch(fmt.length) {
			case 1: case 2: out = y % 100; outl = 2; break;
			default: out = y % 10000; outl = 4; break;
		} break;
		case 109: /* 'm' month */
		switch(fmt.length) {
			case 1: case 2: out = val.m; outl = fmt.length; break;
			case 3: return months[val.m-1][1];
			case 5: return months[val.m-1][0];
			default: return months[val.m-1][2];
		} break;
		case 100: /* 'd' day */
		switch(fmt.length) {
			case 1: case 2: out = val.d; outl = fmt.length; break;
			case 3: return days[val.q][0];
			default: return days[val.q][1];
		} break;
		case 104: /* 'h' 12-hour */
		switch(fmt.length) {
			case 1: case 2: out = 1+(val.H+11)%12; outl = fmt.length; break;
			default: throw 'bad hour format: ' + fmt;
		} break;
		case 72: /* 'H' 24-hour */
		switch(fmt.length) {
			case 1: case 2: out = val.H; outl = fmt.length; break;
			default: throw 'bad hour format: ' + fmt;
		} break;
		case 77: /* 'M' minutes */
		switch(fmt.length) {
			case 1: case 2: out = val.M; outl = fmt.length; break;
			default: throw 'bad minute format: ' + fmt;
		} break;
		case 115: /* 's' seconds */
		if(val.u === 0) switch(fmt) {
			case 's': case 'ss': return pad0(val.S, fmt.length);
			case '.0': case '.00': case '.000':
		}
		switch(fmt) {
			case 's': case 'ss': case '.0': case '.00': case '.000':
if(ss0 >= 2) tt = ss0 === 3 ? 1000 : 100;
				else tt = ss0 === 1 ? 10 : 1;
				ss = Math.round((tt)*(val.S + val.u));
				if(ss >= 60*tt) ss = 0;
				if(fmt === 's') return ss === 0 ? "0" : ""+ss/tt;
				o = pad0(ss,2 + ss0);
				if(fmt === 'ss') return o.substr(0,2);
				return "." + o.substr(2,fmt.length-1);
			default: throw 'bad second format: ' + fmt;
		}
		case 90: /* 'Z' absolute time */
		switch(fmt) {
			case '[h]': case '[hh]': out = val.D*24+val.H; break;
			case '[m]': case '[mm]': out = (val.D*24+val.H)*60+val.M; break;
			case '[s]': case '[ss]': out = ((val.D*24+val.H)*60+val.M)*60+Math.round(val.S+val.u); break;
			default: throw 'bad abstime format: ' + fmt;
		} outl = fmt.length === 3 ? 1 : 2; break;
		case 101: /* 'e' era */
			out = y; outl = 1;
	}
	if(outl > 0) return pad0(out, outl); else return "";
}
/*jshint +W086 */
function commaify(s) {
	if(s.length <= 3) return s;
	var j = (s.length % 3), o = s.substr(0,j);
	for(; j!=s.length; j+=3) o+=(o.length > 0 ? "," : "") + s.substr(j,3);
	return o;
}
var write_num = (function make_write_num(){
var pct1 = /%/g;
function write_num_pct(type, fmt, val){
	var sfmt = fmt.replace(pct1,""), mul = fmt.length - sfmt.length;
	return write_num(type, sfmt, val * Math.pow(10,2*mul)) + fill("%",mul);
}
function write_num_cm(type, fmt, val){
	var idx = fmt.length - 1;
	while(fmt.charCodeAt(idx-1) === 44) --idx;
	return write_num(type, fmt.substr(0,idx), val / Math.pow(10,3*(fmt.length-idx)));
}
function write_num_exp(fmt, val){
	var o;
	var idx = fmt.indexOf("E") - fmt.indexOf(".") - 1;
	if(fmt.match(/^#+0.0E\+0$/)) {
		if(val == 0) return "0.0E+0";
		else if(val < 0) return "-" + write_num_exp(fmt, -val);
		var period = fmt.indexOf("."); if(period === -1) period=fmt.indexOf('E');
		var ee = Math.floor(Math.log(val)*Math.LOG10E)%period;
		if(ee < 0) ee += period;
		o = (val/Math.pow(10,ee)).toPrecision(idx+1+(period+ee)%period);
		if(o.indexOf("e") === -1) {
			var fakee = Math.floor(Math.log(val)*Math.LOG10E);
			if(o.indexOf(".") === -1) o = o.charAt(0) + "." + o.substr(1) + "E+" + (fakee - o.length+ee);
			else o += "E+" + (fakee - ee);
			while(o.substr(0,2) === "0.") {
				o = o.charAt(0) + o.substr(2,period) + "." + o.substr(2+period);
				o = o.replace(/^0+([1-9])/,"$1").replace(/^0+\./,"0.");
			}
			o = o.replace(/\+-/,"-");
		}
		o = o.replace(/^([+-]?)(\d*)\.(\d*)[Ee]/,function($$,$1,$2,$3) { return $1 + $2 + $3.substr(0,(period+ee)%period) + "." + $3.substr(ee) + "E"; });
	} else o = val.toExponential(idx);
	if(fmt.match(/E\+00$/) && o.match(/e[+-]\d$/)) o = o.substr(0,o.length-1) + "0" + o.charAt(o.length-1);
	if(fmt.match(/E\-/) && o.match(/e\+/)) o = o.replace(/e\+/,"e");
	return o.replace("e","E");
}
var frac1 = /# (\?+)( ?)\/( ?)(\d+)/;
function write_num_f1(r, aval, sign) {
	var den = parseInt(r[4],10), rr = Math.round(aval * den), base = Math.floor(rr/den);
	var myn = (rr - base*den), myd = den;
	return sign + (base === 0 ? "" : ""+base) + " " + (myn === 0 ? fill(" ", r[1].length + 1 + r[4].length) : pad_(myn,r[1].length) + r[2] + "/" + r[3] + pad0(myd,r[4].length));
}
function write_num_f2(r, aval, sign) {
	return sign + (aval === 0 ? "" : ""+aval) + fill(" ", r[1].length + 2 + r[4].length);
}
var dec1 = /^#*0*\.(0+)/;
var closeparen = /\).*[0#]/;
var phone = /\(###\) ###\\?-####/;
function hashq(str) {
	var o = "", cc;
	for(var i = 0; i != str.length; ++i) switch((cc=str.charCodeAt(i))) {
		case 35: break;
		case 63: o+= " "; break;
		case 48: o+= "0"; break;
		default: o+= String.fromCharCode(cc);
	}
	return o;
}
function rnd(val, d) { var dd = Math.pow(10,d); return ""+(Math.round(val * dd)/dd); }
function dec(val, d) {
	if (d < ('' + Math.round((val-Math.floor(val))*Math.pow(10,d))).length) {
		return 0;
	}
	return Math.round((val-Math.floor(val))*Math.pow(10,d));
}
function carry(val, d) {
	if (d < ('' + Math.round((val-Math.floor(val))*Math.pow(10,d))).length) {
		return 1;
	}
	return 0;
}
function flr(val) { if(val < 2147483647 && val > -2147483648) return ""+(val >= 0 ? (val|0) : (val-1|0)); return ""+Math.floor(val); }
function write_num_flt(type, fmt, val) {
	if(type.charCodeAt(0) === 40 && !fmt.match(closeparen)) {
		var ffmt = fmt.replace(/\( */,"").replace(/ \)/,"").replace(/\)/,"");
		if(val >= 0) return write_num_flt('n', ffmt, val);
		return '(' + write_num_flt('n', ffmt, -val) + ')';
	}
	if(fmt.charCodeAt(fmt.length - 1) === 44) return write_num_cm(type, fmt, val);
	if(fmt.indexOf('%') !== -1) return write_num_pct(type, fmt, val);
	if(fmt.indexOf('E') !== -1) return write_num_exp(fmt, val);
	if(fmt.charCodeAt(0) === 36) return "$"+write_num_flt(type,fmt.substr(fmt.charAt(1)==' '?2:1),val);
	var o;
	var r, ri, ff, aval = Math.abs(val), sign = val < 0 ? "-" : "";
	if(fmt.match(/^00+$/)) return sign + pad0r(aval,fmt.length);
	if(fmt.match(/^[#?]+$/)) {
		o = pad0r(val,0); if(o === "0") o = "";
		return o.length > fmt.length ? o : hashq(fmt.substr(0,fmt.length-o.length)) + o;
	}
	if((r = fmt.match(frac1))) return write_num_f1(r, aval, sign);
	if(fmt.match(/^#+0+$/)) return sign + pad0r(aval,fmt.length - fmt.indexOf("0"));
	if((r = fmt.match(dec1))) {
		o = rnd(val, r[1].length).replace(/^([^\.]+)$/,"$1."+r[1]).replace(/\.$/,"."+r[1]).replace(/\.(\d*)$/,function($$, $1) { return "." + $1 + fill("0", r[1].length-$1.length); });
		return fmt.indexOf("0.") !== -1 ? o : o.replace(/^0\./,".");
	}
	fmt = fmt.replace(/^#+([0.])/, "$1");
	if((r = fmt.match(/^(0*)\.(#*)$/))) {
		return sign + rnd(aval, r[2].length).replace(/\.(\d*[1-9])0*$/,".$1").replace(/^(-?\d*)$/,"$1.").replace(/^0\./,r[1].length?"0.":".");
	}
	if((r = fmt.match(/^#{1,3},##0(\.?)$/))) return sign + commaify(pad0r(aval,0));
	if((r = fmt.match(/^#,##0\.([#0]*0)$/))) {
		return val < 0 ? "-" + write_num_flt(type, fmt, -val) : commaify(""+(Math.floor(val) + carry(val, r[1].length))) + "." + pad0(dec(val, r[1].length),r[1].length);
	}
	if((r = fmt.match(/^#,#*,#0/))) return write_num_flt(type,fmt.replace(/^#,#*,/,""),val);
	if((r = fmt.match(/^([0#]+)(\\?-([0#]+))+$/))) {
		o = _strrev(write_num_flt(type, fmt.replace(/[\\-]/g,""), val));
		ri = 0;
		return _strrev(_strrev(fmt.replace(/\\/g,"")).replace(/[0#]/g,function(x){return ri<o.length?o.charAt(ri++):x==='0'?'0':"";}));
	}
	if(fmt.match(phone)) {
		o = write_num_flt(type, "##########", val);
		return "(" + o.substr(0,3) + ") " + o.substr(3, 3) + "-" + o.substr(6);
	}
	var oa = "";
	if((r = fmt.match(/^([#0?]+)( ?)\/( ?)([#0?]+)/))) {
		ri = Math.min(r[4].length,7);
		ff = frac(aval, Math.pow(10,ri)-1, false);
		o = "" + sign;
		oa = write_num("n", r[1], ff[1]);
		if(oa.charAt(oa.length-1) == " ") oa = oa.substr(0,oa.length-1) + "0";
		o += oa + r[2] + "/" + r[3];
		oa = rpad_(ff[2],ri);
		if(oa.length < r[4].length) oa = hashq(r[4].substr(r[4].length-oa.length)) + oa;
		o += oa;
		return o;
	}
	if((r = fmt.match(/^# ([#0?]+)( ?)\/( ?)([#0?]+)/))) {
		ri = Math.min(Math.max(r[1].length, r[4].length),7);
		ff = frac(aval, Math.pow(10,ri)-1, true);
		return sign + (ff[0]||(ff[1] ? "" : "0")) + " " + (ff[1] ? pad_(ff[1],ri) + r[2] + "/" + r[3] + rpad_(ff[2],ri): fill(" ", 2*ri+1 + r[2].length + r[3].length));
	}
	if((r = fmt.match(/^[#0?]+$/))) {
		o = pad0r(val, 0);
		if(fmt.length <= o.length) return o;
		return hashq(fmt.substr(0,fmt.length-o.length)) + o;
	}
	if((r = fmt.match(/^([#0?]+)\.([#0]+)$/))) {
		o = "" + val.toFixed(Math.min(r[2].length,10)).replace(/([^0])0+$/,"$1");
		ri = o.indexOf(".");
		var lres = fmt.indexOf(".") - ri, rres = fmt.length - o.length - lres;
		return hashq(fmt.substr(0,lres) + o + fmt.substr(fmt.length-rres));
	}
	if((r = fmt.match(/^00,000\.([#0]*0)$/))) {
		ri = dec(val, r[1].length);
		return val < 0 ? "-" + write_num_flt(type, fmt, -val) : commaify(flr(val)).replace(/^\d,\d{3}$/,"0$&").replace(/^\d*$/,function($$) { return "00," + ($$.length < 3 ? pad0(0,3-$$.length) : "") + $$; }) + "." + pad0(ri,r[1].length);
	}
	switch(fmt) {
		case "###,##0.00": return write_num_flt(type, "#,##0.00", val);
		case "###,###":
		case "##,###":
		case "#,###": var x = commaify(pad0r(aval,0)); return x !== "0" ? sign + x : "";
		case "###,###.00": return write_num_flt(type, "###,##0.00",val).replace(/^0\./,".");
		case "#,###.00": return write_num_flt(type, "#,##0.00",val).replace(/^0\./,".");
		default:
	}
	throw new Error("unsupported format |" + fmt + "|");
}
function write_num_cm2(type, fmt, val){
	var idx = fmt.length - 1;
	while(fmt.charCodeAt(idx-1) === 44) --idx;
	return write_num(type, fmt.substr(0,idx), val / Math.pow(10,3*(fmt.length-idx)));
}
function write_num_pct2(type, fmt, val){
	var sfmt = fmt.replace(pct1,""), mul = fmt.length - sfmt.length;
	return write_num(type, sfmt, val * Math.pow(10,2*mul)) + fill("%",mul);
}
function write_num_exp2(fmt, val){
	var o;
	var idx = fmt.indexOf("E") - fmt.indexOf(".") - 1;
	if(fmt.match(/^#+0.0E\+0$/)) {
		if(val == 0) return "0.0E+0";
		else if(val < 0) return "-" + write_num_exp2(fmt, -val);
		var period = fmt.indexOf("."); if(period === -1) period=fmt.indexOf('E');
		var ee = Math.floor(Math.log(val)*Math.LOG10E)%period;
		if(ee < 0) ee += period;
		o = (val/Math.pow(10,ee)).toPrecision(idx+1+(period+ee)%period);
		if(!o.match(/[Ee]/)) {
			var fakee = Math.floor(Math.log(val)*Math.LOG10E);
			if(o.indexOf(".") === -1) o = o.charAt(0) + "." + o.substr(1) + "E+" + (fakee - o.length+ee);
			else o += "E+" + (fakee - ee);
			o = o.replace(/\+-/,"-");
		}
		o = o.replace(/^([+-]?)(\d*)\.(\d*)[Ee]/,function($$,$1,$2,$3) { return $1 + $2 + $3.substr(0,(period+ee)%period) + "." + $3.substr(ee) + "E"; });
	} else o = val.toExponential(idx);
	if(fmt.match(/E\+00$/) && o.match(/e[+-]\d$/)) o = o.substr(0,o.length-1) + "0" + o.charAt(o.length-1);
	if(fmt.match(/E\-/) && o.match(/e\+/)) o = o.replace(/e\+/,"e");
	return o.replace("e","E");
}
function write_num_int(type, fmt, val) {
	if(type.charCodeAt(0) === 40 && !fmt.match(closeparen)) {
		var ffmt = fmt.replace(/\( */,"").replace(/ \)/,"").replace(/\)/,"");
		if(val >= 0) return write_num_int('n', ffmt, val);
		return '(' + write_num_int('n', ffmt, -val) + ')';
	}
	if(fmt.charCodeAt(fmt.length - 1) === 44) return write_num_cm2(type, fmt, val);
	if(fmt.indexOf('%') !== -1) return write_num_pct2(type, fmt, val);
	if(fmt.indexOf('E') !== -1) return write_num_exp2(fmt, val);
	if(fmt.charCodeAt(0) === 36) return "$"+write_num_int(type,fmt.substr(fmt.charAt(1)==' '?2:1),val);
	var o;
	var r, ri, ff, aval = Math.abs(val), sign = val < 0 ? "-" : "";
	if(fmt.match(/^00+$/)) return sign + pad0(aval,fmt.length);
	if(fmt.match(/^[#?]+$/)) {
		o = (""+val); if(val === 0) o = "";
		return o.length > fmt.length ? o : hashq(fmt.substr(0,fmt.length-o.length)) + o;
	}
	if((r = fmt.match(frac1))) return write_num_f2(r, aval, sign);
	if(fmt.match(/^#+0+$/)) return sign + pad0(aval,fmt.length - fmt.indexOf("0"));
	if((r = fmt.match(dec1))) {
o = (""+val).replace(/^([^\.]+)$/,"$1."+r[1]).replace(/\.$/,"."+r[1]);
		o = o.replace(/\.(\d*)$/,function($$, $1) {
return "." + $1 + fill("0", r[1].length-$1.length); });
		return fmt.indexOf("0.") !== -1 ? o : o.replace(/^0\./,".");
	}
	fmt = fmt.replace(/^#+([0.])/, "$1");
	if((r = fmt.match(/^(0*)\.(#*)$/))) {
		return sign + (""+aval).replace(/\.(\d*[1-9])0*$/,".$1").replace(/^(-?\d*)$/,"$1.").replace(/^0\./,r[1].length?"0.":".");
	}
	if((r = fmt.match(/^#{1,3},##0(\.?)$/))) return sign + commaify((""+aval));
	if((r = fmt.match(/^#,##0\.([#0]*0)$/))) {
		return val < 0 ? "-" + write_num_int(type, fmt, -val) : commaify((""+val)) + "." + fill('0',r[1].length);
	}
	if((r = fmt.match(/^#,#*,#0/))) return write_num_int(type,fmt.replace(/^#,#*,/,""),val);
	if((r = fmt.match(/^([0#]+)(\\?-([0#]+))+$/))) {
		o = _strrev(write_num_int(type, fmt.replace(/[\\-]/g,""), val));
		ri = 0;
		return _strrev(_strrev(fmt.replace(/\\/g,"")).replace(/[0#]/g,function(x){return ri<o.length?o.charAt(ri++):x==='0'?'0':"";}));
	}
	if(fmt.match(phone)) {
		o = write_num_int(type, "##########", val);
		return "(" + o.substr(0,3) + ") " + o.substr(3, 3) + "-" + o.substr(6);
	}
	var oa = "";
	if((r = fmt.match(/^([#0?]+)( ?)\/( ?)([#0?]+)/))) {
		ri = Math.min(r[4].length,7);
		ff = frac(aval, Math.pow(10,ri)-1, false);
		o = "" + sign;
		oa = write_num("n", r[1], ff[1]);
		if(oa.charAt(oa.length-1) == " ") oa = oa.substr(0,oa.length-1) + "0";
		o += oa + r[2] + "/" + r[3];
		oa = rpad_(ff[2],ri);
		if(oa.length < r[4].length) oa = hashq(r[4].substr(r[4].length-oa.length)) + oa;
		o += oa;
		return o;
	}
	if((r = fmt.match(/^# ([#0?]+)( ?)\/( ?)([#0?]+)/))) {
		ri = Math.min(Math.max(r[1].length, r[4].length),7);
		ff = frac(aval, Math.pow(10,ri)-1, true);
		return sign + (ff[0]||(ff[1] ? "" : "0")) + " " + (ff[1] ? pad_(ff[1],ri) + r[2] + "/" + r[3] + rpad_(ff[2],ri): fill(" ", 2*ri+1 + r[2].length + r[3].length));
	}
	if((r = fmt.match(/^[#0?]+$/))) {
		o = "" + val;
		if(fmt.length <= o.length) return o;
		return hashq(fmt.substr(0,fmt.length-o.length)) + o;
	}
	if((r = fmt.match(/^([#0]+)\.([#0]+)$/))) {
		o = "" + val.toFixed(Math.min(r[2].length,10)).replace(/([^0])0+$/,"$1");
		ri = o.indexOf(".");
		var lres = fmt.indexOf(".") - ri, rres = fmt.length - o.length - lres;
		return hashq(fmt.substr(0,lres) + o + fmt.substr(fmt.length-rres));
	}
	if((r = fmt.match(/^00,000\.([#0]*0)$/))) {
		return val < 0 ? "-" + write_num_int(type, fmt, -val) : commaify(""+val).replace(/^\d,\d{3}$/,"0$&").replace(/^\d*$/,function($$) { return "00," + ($$.length < 3 ? pad0(0,3-$$.length) : "") + $$; }) + "." + pad0(0,r[1].length);
	}
	switch(fmt) {
		case "###,###":
		case "##,###":
		case "#,###": var x = commaify(""+aval); return x !== "0" ? sign + x : "";
		default:
			if(fmt.match(/\.[0#?]*$/)) return write_num_int(type, fmt.slice(0,fmt.lastIndexOf(".")), val) + hashq(fmt.slice(fmt.lastIndexOf(".")));
	}
	throw new Error("unsupported format |" + fmt + "|");
}
return function write_num(type, fmt, val) {
	return (val|0) === val ? write_num_int(type, fmt, val) : write_num_flt(type, fmt, val);
};})();
function split_fmt(fmt) {
	var out = [];
	var in_str = false/*, cc*/;
	for(var i = 0, j = 0; i < fmt.length; ++i) switch((/*cc=*/fmt.charCodeAt(i))) {
		case 34: /* '"' */
			in_str = !in_str; break;
		case 95: case 42: case 92: /* '_' '*' '\\' */
			++i; break;
		case 59: /* ';' */
			out[out.length] = fmt.substr(j,i-j);
			j = i+1;
	}
	out[out.length] = fmt.substr(j);
	if(in_str === true) throw new Error("Format |" + fmt + "| unterminated string ");
	return out;
}
SSF._split = split_fmt;
var abstime = /\[[HhMmSs]*\]/;
function fmt_is_date(fmt) {
	var i = 0, /*cc = 0,*/ c = "", o = "";
	while(i < fmt.length) {
		switch((c = fmt.charAt(i))) {
			case 'G': if(isgeneral(fmt, i)) i+= 6; i++; break;
			case '"': for(;(/*cc=*/fmt.charCodeAt(++i)) !== 34 && i < fmt.length;) ++i; ++i; break;
			case '\\': i+=2; break;
			case '_': i+=2; break;
			case '@': ++i; break;
			case 'B': case 'b':
				if(fmt.charAt(i+1) === "1" || fmt.charAt(i+1) === "2") return true;
				/* falls through */
			case 'M': case 'D': case 'Y': case 'H': case 'S': case 'E':
				/* falls through */
			case 'm': case 'd': case 'y': case 'h': case 's': case 'e': case 'g': return true;
			case 'A':
				if(fmt.substr(i, 3) === "A/P") return true;
				if(fmt.substr(i, 5) === "AM/PM") return true;
				++i; break;
			case '[':
				o = c;
				while(fmt.charAt(i++) !== ']' && i < fmt.length) o += fmt.charAt(i);
				if(o.match(abstime)) return true;
				break;
			case '.':
				/* falls through */
			case '0': case '#':
				while(i < fmt.length && ("0#?.,E+-%".indexOf(c=fmt.charAt(++i)) > -1 || (c=='\\' && fmt.charAt(i+1) == "-" && "0#".indexOf(fmt.charAt(i+2))>-1))){/* empty */}
				break;
			case '?': while(fmt.charAt(++i) === c){/* empty */} break;
			case '*': ++i; if(fmt.charAt(i) == ' ' || fmt.charAt(i) == '*') ++i; break;
			case '(': case ')': ++i; break;
			case '1': case '2': case '3': case '4': case '5': case '6': case '7': case '8': case '9':
				while(i < fmt.length && "0123456789".indexOf(fmt.charAt(++i)) > -1){/* empty */} break;
			case ' ': ++i; break;
			default: ++i; break;
		}
	}
	return false;
}
SSF.is_date = fmt_is_date;
function eval_fmt(fmt, v, opts, flen) {
	var out = [], o = "", i = 0, c = "", lst='t', q, dt, j, cc;
	var hr='H';
	/* Tokenize */
	while(i < fmt.length) {
		switch((c = fmt.charAt(i))) {
			case 'G': /* General */
				if(!isgeneral(fmt, i)) throw new Error('unrecognized character ' + c + ' in ' +fmt);
				out[out.length] = {t:'G', v:'General'}; i+=7; break;
			case '"': /* Literal text */
				for(o="";(cc=fmt.charCodeAt(++i)) !== 34 && i < fmt.length;) o += String.fromCharCode(cc);
				out[out.length] = {t:'t', v:o}; ++i; break;
			case '\\': var w = fmt.charAt(++i), t = (w === "(" || w === ")") ? w : 't';
				out[out.length] = {t:t, v:w}; ++i; break;
			case '_': out[out.length] = {t:'t', v:" "}; i+=2; break;
			case '@': /* Text Placeholder */
				out[out.length] = {t:'T', v:v}; ++i; break;
			case 'B': case 'b':
				if(fmt.charAt(i+1) === "1" || fmt.charAt(i+1) === "2") {
					if(dt==null) { dt=parse_date_code(v, opts, fmt.charAt(i+1) === "2"); if(dt==null) return ""; }
					out[out.length] = {t:'X', v:fmt.substr(i,2)}; lst = c; i+=2; break;
				}
				/* falls through */
			case 'M': case 'D': case 'Y': case 'H': case 'S': case 'E':
				c = c.toLowerCase();
				/* falls through */
			case 'm': case 'd': case 'y': case 'h': case 's': case 'e': case 'g':
				if(v < 0) return "";
				if(dt==null) { dt=parse_date_code(v, opts); if(dt==null) return ""; }
				o = c; while(++i<fmt.length && fmt.charAt(i).toLowerCase() === c) o+=c;
				if(c === 'm' && lst.toLowerCase() === 'h') c = 'M';
				if(c === 'h') c = hr;
				out[out.length] = {t:c, v:o}; lst = c; break;
			case 'A':
				q={t:c, v:"A"};
				if(dt==null) dt=parse_date_code(v, opts);
				if(fmt.substr(i, 3) === "A/P") { if(dt!=null) q.v = dt.H >= 12 ? "P" : "A"; q.t = 'T'; hr='h';i+=3;}
				else if(fmt.substr(i,5) === "AM/PM") { if(dt!=null) q.v = dt.H >= 12 ? "PM" : "AM"; q.t = 'T'; i+=5; hr='h'; }
				else { q.t = "t"; ++i; }
				if(dt==null && q.t === 'T') return "";
				out[out.length] = q; lst = c; break;
			case '[':
				o = c;
				while(fmt.charAt(i++) !== ']' && i < fmt.length) o += fmt.charAt(i);
				if(o.slice(-1) !== ']') throw 'unterminated "[" block: |' + o + '|';
				if(o.match(abstime)) {
					if(dt==null) { dt=parse_date_code(v, opts); if(dt==null) return ""; }
					out[out.length] = {t:'Z', v:o.toLowerCase()};
					lst = o.charAt(1);
				} else if(o.indexOf("$") > -1) {
					o = (o.match(/\$([^-\[\]]*)/)||[])[1]||"$";
					if(!fmt_is_date(fmt)) out[out.length] = {t:'t',v:o};
				}
				break;
			/* Numbers */
			case '.':
				if(dt != null) {
					o = c; while((c=fmt.charAt(++i)) === "0") o += c;
					out[out.length] = {t:'s', v:o}; break;
				}
				/* falls through */
			case '0': case '#':
				o = c; while((++i < fmt.length && "0#?.,E+-%".indexOf(c=fmt.charAt(i)) > -1) || (c=='\\' && fmt.charAt(i+1) == "-" && i < fmt.length - 2 && "0#".indexOf(fmt.charAt(i+2))>-1)) o += c;
				out[out.length] = {t:'n', v:o}; break;
			case '?':
				o = c; while(fmt.charAt(++i) === c) o+=c;
				q={t:c, v:o}; out[out.length] = q; lst = c; break;
			case '*': ++i; if(fmt.charAt(i) == ' ' || fmt.charAt(i) == '*') ++i; break; // **
			case '(': case ')': out[out.length] = {t:(flen===1?'t':c), v:c}; ++i; break;
			case '1': case '2': case '3': case '4': case '5': case '6': case '7': case '8': case '9':
				o = c; while(i < fmt.length && "0123456789".indexOf(fmt.charAt(++i)) > -1) o+=fmt.charAt(i);
				out[out.length] = {t:'D', v:o}; break;
			case ' ': out[out.length] = {t:c, v:c}; ++i; break;
			default:
				if(",$-+/():!^&'~{}<>=€acfijklopqrtuvwxz".indexOf(c) === -1) throw new Error('unrecognized character ' + c + ' in ' + fmt);
				out[out.length] = {t:'t', v:c}; ++i; break;
		}
	}
	var bt = 0, ss0 = 0, ssm;
	for(i=out.length-1, lst='t'; i >= 0; --i) {
		switch(out[i].t) {
			case 'h': case 'H': out[i].t = hr; lst='h'; if(bt < 1) bt = 1; break;
			case 's':
				if((ssm=out[i].v.match(/\.0+$/))) ss0=Math.max(ss0,ssm[0].length-1);
				if(bt < 3) bt = 3;
			/* falls through */
			case 'd': case 'y': case 'M': case 'e': lst=out[i].t; break;
			case 'm': if(lst === 's') { out[i].t = 'M'; if(bt < 2) bt = 2; } break;
			case 'X': /*if(out[i].v === "B2");*/
				break;
			case 'Z':
				if(bt < 1 && out[i].v.match(/[Hh]/)) bt = 1;
				if(bt < 2 && out[i].v.match(/[Mm]/)) bt = 2;
				if(bt < 3 && out[i].v.match(/[Ss]/)) bt = 3;
		}
	}
	switch(bt) {
		case 0: break;
		case 1:
if(dt.u >= 0.5) { dt.u = 0; ++dt.S; }
			if(dt.S >=  60) { dt.S = 0; ++dt.M; }
			if(dt.M >=  60) { dt.M = 0; ++dt.H; }
			break;
		case 2:
if(dt.u >= 0.5) { dt.u = 0; ++dt.S; }
			if(dt.S >=  60) { dt.S = 0; ++dt.M; }
			break;
	}
	/* replace fields */
	var nstr = "", jj;
	for(i=0; i < out.length; ++i) {
		switch(out[i].t) {
			case 't': case 'T': case ' ': case 'D': break;
			case 'X': out[i].v = ""; out[i].t = ";"; break;
			case 'd': case 'm': case 'y': case 'h': case 'H': case 'M': case 's': case 'e': case 'b': case 'Z':
out[i].v = write_date(out[i].t.charCodeAt(0), out[i].v, dt, ss0);
				out[i].t = 't'; break;
			case 'n': case '(': case '?':
				jj = i+1;
				while(out[jj] != null && (
					(c=out[jj].t) === "?" || c === "D" ||
					((c === " " || c === "t") && out[jj+1] != null && (out[jj+1].t === '?' || out[jj+1].t === "t" && out[jj+1].v === '/')) ||
					(out[i].t === '(' && (c === ' ' || c === 'n' || c === ')')) ||
					(c === 't' && (out[jj].v === '/' || out[jj].v === ' ' && out[jj+1] != null && out[jj+1].t == '?'))
				)) {
					out[i].v += out[jj].v;
					out[jj] = {v:"", t:";"}; ++jj;
				}
				nstr += out[i].v;
				i = jj-1; break;
			case 'G': out[i].t = 't'; out[i].v = general_fmt(v,opts); break;
		}
	}
	var vv = "", myv, ostr;
	if(nstr.length > 0) {
		if(nstr.charCodeAt(0) == 40) /* '(' */ {
			myv = (v<0&&nstr.charCodeAt(0) === 45 ? -v : v);
			ostr = write_num('(', nstr, myv);
		} else {
			myv = (v<0 && flen > 1 ? -v : v);
			ostr = write_num('n', nstr, myv);
			if(myv < 0 && out[0] && out[0].t == 't') {
				ostr = ostr.substr(1);
				out[0].v = "-" + out[0].v;
			}
		}
		jj=ostr.length-1;
		var decpt = out.length;
		for(i=0; i < out.length; ++i) if(out[i] != null && out[i].t != 't' && out[i].v.indexOf(".") > -1) { decpt = i; break; }
		var lasti=out.length;
		if(decpt === out.length && ostr.indexOf("E") === -1) {
			for(i=out.length-1; i>= 0;--i) {
				if(out[i] == null || 'n?('.indexOf(out[i].t) === -1) continue;
				if(jj>=out[i].v.length-1) { jj -= out[i].v.length; out[i].v = ostr.substr(jj+1, out[i].v.length); }
				else if(jj < 0) out[i].v = "";
				else { out[i].v = ostr.substr(0, jj+1); jj = -1; }
				out[i].t = 't';
				lasti = i;
			}
			if(jj>=0 && lasti<out.length) out[lasti].v = ostr.substr(0,jj+1) + out[lasti].v;
		}
		else if(decpt !== out.length && ostr.indexOf("E") === -1) {
			jj = ostr.indexOf(".")-1;
			for(i=decpt; i>= 0; --i) {
				if(out[i] == null || 'n?('.indexOf(out[i].t) === -1) continue;
				j=out[i].v.indexOf(".")>-1&&i===decpt?out[i].v.indexOf(".")-1:out[i].v.length-1;
				vv = out[i].v.substr(j+1);
				for(; j>=0; --j) {
					if(jj>=0 && (out[i].v.charAt(j) === "0" || out[i].v.charAt(j) === "#")) vv = ostr.charAt(jj--) + vv;
				}
				out[i].v = vv;
				out[i].t = 't';
				lasti = i;
			}
			if(jj>=0 && lasti<out.length) out[lasti].v = ostr.substr(0,jj+1) + out[lasti].v;
			jj = ostr.indexOf(".")+1;
			for(i=decpt; i<out.length; ++i) {
				if(out[i] == null || ('n?('.indexOf(out[i].t) === -1 && i !== decpt)) continue;
				j=out[i].v.indexOf(".")>-1&&i===decpt?out[i].v.indexOf(".")+1:0;
				vv = out[i].v.substr(0,j);
				for(; j<out[i].v.length; ++j) {
					if(jj<ostr.length) vv += ostr.charAt(jj++);
				}
				out[i].v = vv;
				out[i].t = 't';
				lasti = i;
			}
		}
	}
	for(i=0; i<out.length; ++i) if(out[i] != null && 'n(?'.indexOf(out[i].t)>-1) {
		myv = (flen >1 && v < 0 && i>0 && out[i-1].v === "-" ? -v:v);
		out[i].v = write_num(out[i].t, out[i].v, myv);
		out[i].t = 't';
	}
	var retval = "";
	for(i=0; i !== out.length; ++i) if(out[i] != null) retval += out[i].v;
	return retval;
}
SSF._eval = eval_fmt;
var cfregex = /\[[=<>]/;
var cfregex2 = /\[([=<>]*)(-?\d+\.?\d*)\]/;
function chkcond(v, rr) {
	if(rr == null) return false;
	var thresh = parseFloat(rr[2]);
	switch(rr[1]) {
		case "=":  if(v == thresh) return true; break;
		case ">":  if(v >  thresh) return true; break;
		case "<":  if(v <  thresh) return true; break;
		case "<>": if(v != thresh) return true; break;
		case ">=": if(v >= thresh) return true; break;
		case "<=": if(v <= thresh) return true; break;
	}
	return false;
}
function choose_fmt(f, v) {
	var fmt = split_fmt(f);
	var l = fmt.length, lat = fmt[l-1].indexOf("@");
	if(l<4 && lat>-1) --l;
	if(fmt.length > 4) throw new Error("cannot find right format for |" + fmt.join("|") + "|");
	if(typeof v !== "number") return [4, fmt.length === 4 || lat>-1?fmt[fmt.length-1]:"@"];
	switch(fmt.length) {
		case 1: fmt = lat>-1 ? ["General", "General", "General", fmt[0]] : [fmt[0], fmt[0], fmt[0], "@"]; break;
		case 2: fmt = lat>-1 ? [fmt[0], fmt[0], fmt[0], fmt[1]] : [fmt[0], fmt[1], fmt[0], "@"]; break;
		case 3: fmt = lat>-1 ? [fmt[0], fmt[1], fmt[0], fmt[2]] : [fmt[0], fmt[1], fmt[2], "@"]; break;
		case 4: break;
	}
	var ff = v > 0 ? fmt[0] : v < 0 ? fmt[1] : fmt[2];
	if(fmt[0].indexOf("[") === -1 && fmt[1].indexOf("[") === -1) return [l, ff];
	if(fmt[0].match(cfregex) != null || fmt[1].match(cfregex) != null) {
		var m1 = fmt[0].match(cfregex2);
		var m2 = fmt[1].match(cfregex2);
		return chkcond(v, m1) ? [l, fmt[0]] : chkcond(v, m2) ? [l, fmt[1]] : [l, fmt[m1 != null && m2 != null ? 2 : 1]];
	}
	return [l, ff];
}
function format(fmt,v,o) {
	if(o == null) o = {};
	var sfmt = "";
	switch(typeof fmt) {
		case "string":
			if(fmt == "m/d/yy" && o.dateNF) sfmt = o.dateNF;
			else sfmt = fmt;
			break;
		case "number":
			if(fmt == 14 && o.dateNF) sfmt = o.dateNF;
			else sfmt = (o.table != null ? (o.table) : table_fmt)[fmt];
			break;
	}
	if(isgeneral(sfmt,0)) return general_fmt(v, o);
	var f = choose_fmt(sfmt, v);
	if(isgeneral(f[1])) return general_fmt(v, o);
	if(v === true) v = "TRUE"; else if(v === false) v = "FALSE";
	else if(v === "" || v == null) return "";
	return eval_fmt(f[1], v, o, f[0]);
}
SSF._table = table_fmt;
SSF.load = function load_entry(fmt, idx) { table_fmt[idx] = fmt; };
SSF.format = format;
SSF.get_table = function get_table() { return table_fmt; };
SSF.load_table = function load_table(tbl) { for(var i=0; i!=0x0188; ++i) if(tbl[i] !== undefined) SSF.load(tbl[i], i); };
SSF.init_table = init_table;
};
make_ssf(SSF);
/* map from xlml named formats to SSF TODO: localize */
var XLMLFormatMap/*{[string]:string}*/ = ({
	"General Number": "General",
	"General Date": SSF._table[22],
	"Long Date": "dddd, mmmm dd, yyyy",
	"Medium Date": SSF._table[15],
	"Short Date": SSF._table[14],
	"Long Time": SSF._table[19],
	"Medium Time": SSF._table[18],
	"Short Time": SSF._table[20],
	"Currency": '"$"#,##0.00_);[Red]\\("$"#,##0.00\\)',
	"Fixed": SSF._table[2],
	"Standard": SSF._table[4],
	"Percent": SSF._table[10],
	"Scientific": SSF._table[11],
	"Yes/No": '"Yes";"Yes";"No";@',
	"True/False": '"True";"True";"False";@',
	"On/Off": '"Yes";"Yes";"No";@'
});

var DO_NOT_EXPORT_CFB = true;
/* cfb.js (C) 2013-present SheetJS -- http://sheetjs.com */
/* vim: set ts=2: */
/*jshint eqnull:true */

/* [MS-CFB] v20130118 */
var CFB = (function _CFB(){
var exports = {};
exports.version = '0.11.1';
function parse(file) {
var mver = 3; // major version
var ssz = 512; // sector size
var nmfs = 0; // number of mini FAT sectors
var ndfs = 0; // number of DIFAT sectors
var dir_start = 0; // first directory sector location
var minifat_start = 0; // first mini FAT sector location
var difat_start = 0; // first mini FAT sector location

var fat_addrs = []; // locations of FAT sectors

/* [MS-CFB] 2.2 Compound File Header */
var blob = file.slice(0,512);
prep_blob(blob, 0);

/* major version */
var mv = check_get_mver(blob);
mver = mv[0];
switch(mver) {
	case 3: ssz = 512; break; case 4: ssz = 4096; break;
	default: throw new Error("Major Version: Expected 3 or 4 saw " + mver);
}

/* reprocess header */
if(ssz !== 512) { blob = file.slice(0,ssz); prep_blob(blob, 28 /* blob.l */); }
/* Save header for final object */
var header = file.slice(0,ssz);

check_shifts(blob, mver);

// Number of Directory Sectors
var nds = blob.read_shift(4, 'i');
if(mver === 3 && nds !== 0) throw new Error('# Directory Sectors: Expected 0 saw ' + nds);

// Number of FAT Sectors
//var nfs = blob.read_shift(4, 'i');
blob.l += 4;

// First Directory Sector Location
dir_start = blob.read_shift(4, 'i');

// Transaction Signature
blob.l += 4;

// Mini Stream Cutoff Size
blob.chk('00100000', 'Mini Stream Cutoff Size: ');

// First Mini FAT Sector Location
minifat_start = blob.read_shift(4, 'i');

// Number of Mini FAT Sectors
nmfs = blob.read_shift(4, 'i');

// First DIFAT sector location
difat_start = blob.read_shift(4, 'i');

// Number of DIFAT Sectors
ndfs = blob.read_shift(4, 'i');

// Grab FAT Sector Locations
for(var q, j = 0; j < 109; ++j) { /* 109 = (512 - blob.l)>>>2; */
	q = blob.read_shift(4, 'i');
	if(q<0) break;
	fat_addrs[j] = q;
}

/** Break the file up into sectors */
var sectors = sectorify(file, ssz);

sleuth_fat(difat_start, ndfs, sectors, ssz, fat_addrs);

/** Chains */
var sector_list = make_sector_list(sectors, dir_start, fat_addrs, ssz);

sector_list[dir_start].name = "!Directory";
if(nmfs > 0 && minifat_start !== ENDOFCHAIN) sector_list[minifat_start].name = "!MiniFAT";
sector_list[fat_addrs[0]].name = "!FAT";
sector_list.fat_addrs = fat_addrs;
sector_list.ssz = ssz;

/* [MS-CFB] 2.6.1 Compound File Directory Entry */
var files = {}, Paths = [], FileIndex = [], FullPaths = [], FullPathDir = {};
read_directory(dir_start, sector_list, sectors, Paths, nmfs, files, FileIndex);

build_full_paths(FileIndex, FullPathDir, FullPaths, Paths);

var root_name = Paths.shift();
Paths.root = root_name;

/* [MS-CFB] 2.6.4 (Unicode 3.0.1 case conversion) */
var find_path = make_find_path(FullPaths, Paths, FileIndex, files, root_name);

return {
	raw: {header: header, sectors: sectors},
	FileIndex: FileIndex,
	FullPaths: FullPaths,
	FullPathDir: FullPathDir,
	find: find_path
};
} // parse

/* [MS-CFB] 2.2 Compound File Header -- read up to major version */
function check_get_mver(blob) {
	// header signature 8
	blob.chk(HEADER_SIGNATURE, 'Header Signature: ');

	// clsid 16
	blob.chk(HEADER_CLSID, 'CLSID: ');

	// minor version 2
	var mver = blob.read_shift(2, 'u');

	return [blob.read_shift(2,'u'), mver];
}
function check_shifts(blob, mver) {
	var shift = 0x09;

	// Byte Order
	//blob.chk('feff', 'Byte Order: '); // note: some writers put 0xffff
	blob.l += 2;

	// Sector Shift
	switch((shift = blob.read_shift(2))) {
		case 0x09: if(mver != 3) throw new Error('Sector Shift: Expected 9 saw ' + shift); break;
		case 0x0c: if(mver != 4) throw new Error('Sector Shift: Expected 12 saw ' + shift); break;
		default: throw new Error('Sector Shift: Expected 9 or 12 saw ' + shift);
	}

	// Mini Sector Shift
	blob.chk('0600', 'Mini Sector Shift: ');

	// Reserved
	blob.chk('000000000000', 'Reserved: ');
}

/** Break the file up into sectors */
function sectorify(file, ssz) {
	var nsectors = Math.ceil(file.length/ssz)-1;
	var sectors = new Array(nsectors);
	for(var i=1; i < nsectors; ++i) sectors[i-1] = file.slice(i*ssz,(i+1)*ssz);
	sectors[nsectors-1] = file.slice(nsectors*ssz);
	return sectors;
}

/* [MS-CFB] 2.6.4 Red-Black Tree */
function build_full_paths(FI, FPD, FP, Paths) {
	var i = 0, L = 0, R = 0, C = 0, j = 0, pl = Paths.length;
	var dad = new Array(pl), q = new Array(pl);

	for(; i < pl; ++i) { dad[i]=q[i]=i; FP[i]=Paths[i]; }

	for(; j < q.length; ++j) {
		i = q[j];
		L = FI[i].L; R = FI[i].R; C = FI[i].C;
		if(dad[i] === i) {
			if(L !== -1 /*NOSTREAM*/ && dad[L] !== L) dad[i] = dad[L];
			if(R !== -1 && dad[R] !== R) dad[i] = dad[R];
		}
		if(C !== -1 /*NOSTREAM*/) dad[C] = i;
		if(L !== -1) { dad[L] = dad[i]; q.push(L); }
		if(R !== -1) { dad[R] = dad[i]; q.push(R); }
	}
	for(i=1; i !== pl; ++i) if(dad[i] === i) {
		if(R !== -1 /*NOSTREAM*/ && dad[R] !== R) dad[i] = dad[R];
		else if(L !== -1 && dad[L] !== L) dad[i] = dad[L];
	}

	for(i=1; i < pl; ++i) {
		if(FI[i].type === 0 /* unknown */) continue;
		j = dad[i];
		if(j === 0) FP[i] = FP[0] + "/" + FP[i];
		else while(j !== 0) {
			FP[i] = FP[j] + "/" + FP[i];
			j = dad[j];
		}
		dad[i] = 0;
	}

	FP[0] += "/";
	for(i=1; i < pl; ++i) {
		if(FI[i].type !== 2 /* stream */) FP[i] += "/";
		FPD[FP[i]] = FI[i];
	}
}

/* [MS-CFB] 2.6.4 */
function make_find_path(FullPaths, Paths, FileIndex, files, root_name) {
	var UCFullPaths = new Array(FullPaths.length);
	var UCPaths = new Array(Paths.length), i;
	for(i = 0; i < FullPaths.length; ++i) UCFullPaths[i] = FullPaths[i].toUpperCase().replace(chr0,'').replace(chr1,'!');
	for(i = 0; i < Paths.length; ++i) UCPaths[i] = Paths[i].toUpperCase().replace(chr0,'').replace(chr1,'!');
	return function find_path(path) {
		var k;
		if(path.charCodeAt(0) === 47 /* "/" */) { k=true; path = root_name + path; }
		else k = path.indexOf("/") !== -1;
		var UCPath = path.toUpperCase().replace(chr0,'').replace(chr1,'!');
		var w = k === true ? UCFullPaths.indexOf(UCPath) : UCPaths.indexOf(UCPath);
		if(w === -1) return null;
		return k === true ? FileIndex[w] : files[Paths[w]];
	};
}

/** Chase down the rest of the DIFAT chain to build a comprehensive list
    DIFAT chains by storing the next sector number as the last 32 bytes */
function sleuth_fat(idx, cnt, sectors, ssz, fat_addrs) {
	var q;
	if(idx === ENDOFCHAIN) {
		if(cnt !== 0) throw new Error("DIFAT chain shorter than expected");
	} else if(idx !== -1 /*FREESECT*/) {
		var sector = sectors[idx], m = (ssz>>>2)-1;
		if(!sector) return;
		for(var i = 0; i < m; ++i) {
			if((q = __readInt32LE(sector,i*4)) === ENDOFCHAIN) break;
			fat_addrs.push(q);
		}
		sleuth_fat(__readInt32LE(sector,ssz-4),cnt - 1, sectors, ssz, fat_addrs);
	}
}

/** Follow the linked list of sectors for a given starting point */
function get_sector_list(sectors, start, fat_addrs, ssz, chkd) {
	var sl = sectors.length;
	var buf, buf_chain;
	if(!chkd) chkd = new Array(sl);
	var modulus = ssz - 1, j, jj;
	buf = [];
	buf_chain = [];
	for(j=start; j>=0;) {
		chkd[j] = true;
		buf[buf.length] = j;
		buf_chain.push(sectors[j]);
		var addr = fat_addrs[Math.floor(j*4/ssz)];
		jj = ((j*4) & modulus);
		if(ssz < 4 + jj) throw new Error("FAT boundary crossed: " + j + " 4 "+ssz);
		if(!sectors[addr]) break;
		j = __readInt32LE(sectors[addr], jj);
	}
	return {nodes: buf, data:__toBuffer([buf_chain])};
}

/** Chase down the sector linked lists */
function make_sector_list(sectors, dir_start, fat_addrs, ssz) {
	var sl = sectors.length, sector_list = new Array(sl);
	var chkd = new Array(sl), buf, buf_chain;
	var modulus = ssz - 1, i, j, k, jj;
	for(i=0; i < sl; ++i) {
		buf = [];
		k = (i + dir_start); if(k >= sl) k-=sl;
		if(chkd[k] === true) continue;
		buf_chain = [];
		for(j=k; j>=0;) {
			chkd[j] = true;
			buf[buf.length] = j;
			buf_chain.push(sectors[j]);
			var addr = fat_addrs[Math.floor(j*4/ssz)];
			jj = ((j*4) & modulus);
			if(ssz < 4 + jj) throw new Error("FAT boundary crossed: " + j + " 4 "+ssz);
			if(!sectors[addr]) break;
			j = __readInt32LE(sectors[addr], jj);
		}
		sector_list[k] = {nodes: buf, data:__toBuffer([buf_chain])};
	}
	return sector_list;
}

/* [MS-CFB] 2.6.1 Compound File Directory Entry */
function read_directory(dir_start, sector_list, sectors, Paths, nmfs, files, FileIndex) {
	var blob;
	var minifat_store = 0, pl = (Paths.length?2:0);
	var sector = sector_list[dir_start].data;
	var i = 0, namelen = 0, name, o, ctime, mtime;
	for(; i < sector.length; i+= 128) {
		blob = sector.slice(i, i+128);
		prep_blob(blob, 64);
		namelen = blob.read_shift(2);
		if(namelen === 0) continue;
		name = __utf16le(blob,0,namelen-pl);
		Paths.push(name);
		o = ({
			name:  name,
			type:  blob.read_shift(1),
			color: blob.read_shift(1),
			L:     blob.read_shift(4, 'i'),
			R:     blob.read_shift(4, 'i'),
			C:     blob.read_shift(4, 'i'),
			clsid: blob.read_shift(16),
			state: blob.read_shift(4, 'i')
		});
		ctime = blob.read_shift(2) + blob.read_shift(2) + blob.read_shift(2) + blob.read_shift(2);
		if(ctime !== 0) {
			o.ctime = ctime; o.ct = read_date(blob, blob.l-8);
		}
		mtime = blob.read_shift(2) + blob.read_shift(2) + blob.read_shift(2) + blob.read_shift(2);
		if(mtime !== 0) {
			o.mtime = mtime; o.mt = read_date(blob, blob.l-8);
		}
		o.start = blob.read_shift(4, 'i');
		o.size = blob.read_shift(4, 'i');
		if(o.type === 5) { /* root */
			minifat_store = o.start;
			if(nmfs > 0 && minifat_store !== ENDOFCHAIN) sector_list[minifat_store].name = "!StreamData";
			/*minifat_size = o.size;*/
		} else if(o.size >= 4096 /* MSCSZ */) {
			o.storage = 'fat';
			if(sector_list[o.start] === undefined) sector_list[o.start] = get_sector_list(sectors, o.start, sector_list.fat_addrs, sector_list.ssz);
			sector_list[o.start].name = o.name;
			o.content = sector_list[o.start].data.slice(0,o.size);
			prep_blob(o.content, 0);
		} else {
			o.storage = 'minifat';
			if(minifat_store !== ENDOFCHAIN && o.start !== ENDOFCHAIN) {
				o.content = sector_list[minifat_store].data.slice(o.start*MSSZ,o.start*MSSZ+o.size);
				prep_blob(o.content, 0);
			}
		}
		files[name] = o;
		FileIndex.push(o);
	}
}

function read_date(blob, offset) {
	return new Date(( ( (__readUInt32LE(blob,offset+4)/1e7)*Math.pow(2,32)+__readUInt32LE(blob,offset)/1e7 ) - 11644473600)*1000);
}

var fs;
function readFileSync(filename, options) {
	if(fs === undefined) fs = require('fs');
	return parse(fs.readFileSync(filename), options);
}

function readSync(blob, options) {
	switch(options !== undefined && options.type !== undefined ? options.type : "base64") {
		case "file": return readFileSync(blob, options);
		case "base64": return parse(s2a(Base64.decode(blob)), options);
		case "binary": return parse(s2a(blob), options);
	}
	return parse(blob);
}

/** CFB Constants */
var MSSZ = 64; /* Mini Sector Size = 1<<6 */
//var MSCSZ = 4096; /* Mini Stream Cutoff Size */
/* 2.1 Compound File Sector Numbers and Types */
var ENDOFCHAIN = -2;
/* 2.2 Compound File Header */
var HEADER_SIGNATURE = 'd0cf11e0a1b11ae1';
var HEADER_CLSID = '00000000000000000000000000000000';
var consts = {
	/* 2.1 Compund File Sector Numbers and Types */
	MAXREGSECT: -6,
	DIFSECT: -4,
	FATSECT: -3,
	ENDOFCHAIN: ENDOFCHAIN,
	FREESECT: -1,
	/* 2.2 Compound File Header */
	HEADER_SIGNATURE: HEADER_SIGNATURE,
	HEADER_MINOR_VERSION: '3e00',
	MAXREGSID: -6,
	NOSTREAM: -1,
	HEADER_CLSID: HEADER_CLSID,
	/* 2.6.1 Compound File Directory Entry */
	EntryTypes: ['unknown','storage','stream','lockbytes','property','root']
};

exports.read = readSync;
exports.parse = parse;
exports.utils = {
	ReadShift: ReadShift,
	CheckField: CheckField,
	prep_blob: prep_blob,
	bconcat: bconcat,
	consts: consts
};

return exports;
})();

if(typeof require !== 'undefined' && typeof module !== 'undefined' && typeof DO_NOT_EXPORT_CFB === 'undefined') { module.exports = CFB; }
function isval(x) { return x !== undefined && x !== null; }

function keys(o) { return Object.keys(o); }

function evert_key(obj, key) {
	var o = ([]), K = keys(obj);
	for(var i = 0; i !== K.length; ++i) o[obj[K[i]][key]] = K[i];
	return o;
}

function evert(obj) {
	var o = ([]), K = keys(obj);
	for(var i = 0; i !== K.length; ++i) o[obj[K[i]]] = K[i];
	return o;
}

function evert_num(obj) {
	var o = ([]), K = keys(obj);
	for(var i = 0; i !== K.length; ++i) o[obj[K[i]]] = parseInt(K[i],10);
	return o;
}

function evert_arr(obj) {
	var o = ([]), K = keys(obj);
	for(var i = 0; i !== K.length; ++i) {
		if(o[obj[K[i]]] == null) o[obj[K[i]]] = [];
		o[obj[K[i]]].push(K[i]);
	}
	return o;
}

function datenum(v, date1904) {
	var epoch = v.getTime();
	if(date1904) epoch += 1462*24*60*60*1000;
	return (epoch + 2209161600000) / (24 * 60 * 60 * 1000);
}
function numdate(v) {
	var date = SSF.parse_date_code(v);
	var val = new Date();
	if(date == null) throw new Error("Bad Date Code: " + v);
	val.setUTCDate(date.d);
	val.setUTCMonth(date.m-1);
	val.setUTCFullYear(date.y);
	val.setUTCHours(date.H);
	val.setUTCMinutes(date.M);
	val.setUTCSeconds(date.S);
	return val;
}

/* ISO 8601 Duration */
function parse_isodur(s) {
	var sec = 0, mt = 0, time = false;
	var m = s.match(/P([0-9\.]+Y)?([0-9\.]+M)?([0-9\.]+D)?T([0-9\.]+H)?([0-9\.]+M)?([0-9\.]+S)?/);
	if(!m) throw new Error("|" + s + "| is not an ISO8601 Duration");
	for(var i = 1; i != m.length; ++i) {
		if(!m[i]) continue;
		mt = 1;
		if(i > 3) time = true;
		switch(m[i].substr(m[i].length-1)) {
			case 'Y':
				throw new Error("Unsupported ISO Duration Field: " + m[i].substr(m[i].length-1));
			case 'D': mt *= 24;
				/* falls through */
			case 'H': mt *= 60;
				/* falls through */
			case 'M':
				if(!time) throw new Error("Unsupported ISO Duration Field: M");
				else mt *= 60;
				/* falls through */
			case 'S': break;
		}
		sec += mt * parseInt(m[i], 10);
	}
	return sec;
}

var good_pd_date = new Date('2017-02-19T19:06:09.000Z');
if(isNaN(good_pd_date.getFullYear())) good_pd_date = new Date('2/19/17');
var good_pd = good_pd_date.getFullYear() == 2017;
function parseDate(str) {
	var d = new Date(str);
	if(good_pd) return d;
	if(str instanceof Date) return str;
	if(good_pd_date.getFullYear() == 1917 && !isNaN(d.getFullYear())) {
		var s = d.getFullYear();
		if(str.indexOf("" + s) > -1) return d;
		d.setFullYear(d.getFullYear() + 100); return d;
	}
	var n = str.match(/\d+/g)||["2017","2","19","0","0","0"];
	return new Date(Date.UTC(+n[0], +n[1] - 1, +n[2], (+n[3]||0), (+n[4]||0), (+n[5]||0)));
}

function cc2str(arr) {
	var o = "";
	for(var i = 0; i != arr.length; ++i) o += String.fromCharCode(arr[i]);
	return o;
}

function str2cc(str) {
	var o = [];
	for(var i = 0; i != str.length; ++i) o.push(str.charCodeAt(i));
	return o;
}

function dup(o) {
	if(typeof JSON != 'undefined' && !Array.isArray(o)) return JSON.parse(JSON.stringify(o));
	if(typeof o != 'object' || o == null) return o;
	var out = {};
	for(var k in o) if(o.hasOwnProperty(k)) out[k] = dup(o[k]);
	return out;
}

function fill(c,l) { var o = ""; while(o.length < l) o+=c; return o; }

/* TODO: stress test */
function fuzzydate(s) {
	var o = new Date(s), n = new Date(NaN);
	var y = o.getYear(), m = o.getMonth(), d = o.getDate();
	if(isNaN(d)) return n;
	if(y < 0 || y > 8099) return n;
	if((m > 0 || d > 1) && y != 101) return o;
	if(s.toLowerCase().match(/jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec/)) return o;
	if(!s.match(/[a-zA-Z]/)) return o;
	return n;
}

function getdatastr(data) {
	if(!data) return null;
	if(data.data) return debom(data.data);
	if(data.asNodeBuffer && has_buf) return debom(data.asNodeBuffer().toString('binary'));
	if(data.asBinary) return debom(data.asBinary());
	if(data._data && data._data.getContent) return debom(cc2str(Array.prototype.slice.call(data._data.getContent(),0)));
	return null;
}

function getdatabin(data) {
	if(!data) return null;
	if(data.data) return char_codes(data.data);
	if(data.asNodeBuffer && has_buf) return data.asNodeBuffer();
	if(data._data && data._data.getContent) {
		var o = data._data.getContent();
		if(typeof o == "string") return str2cc(o);
		return Array.prototype.slice.call(o);
	}
	return null;
}

function getdata(data) { return (data && data.name.slice(-4) === ".bin") ? getdatabin(data) : getdatastr(data); }

/* Part 2 Section 10.1.2 "Mapping Content Types" Names are case-insensitive */
/* OASIS does not comment on filename case sensitivity */
function safegetzipfile(zip, file) {
	var k = keys(zip.files);
	var f = file.toLowerCase(), g = f.replace(/\//g,'\\');
	for(var i=0; i<k.length; ++i) {
		var n = k[i].toLowerCase();
		if(f == n || g == n) return zip.files[k[i]];
	}
	return null;
}

function getzipfile(zip, file) {
	var o = safegetzipfile(zip, file);
	if(o == null) throw new Error("Cannot find file " + file + " in zip");
	return o;
}

function getzipdata(zip, file, safe) {
	if(!safe) return getdata(getzipfile(zip, file));
	if(!file) return null;
	try { return getzipdata(zip, file); } catch(e) { return null; }
}

function getzipstr(zip, file, safe) {
	if(!safe) return getdatastr(getzipfile(zip, file));
	if(!file) return null;
	try { return getzipstr(zip, file); } catch(e) { return null; }
}

var _fs, jszip;
/*global JSZip:true */
if(typeof JSZip !== 'undefined') jszip = JSZip;
if (typeof exports !== 'undefined') {
	if (typeof module !== 'undefined' && module.exports) {
		if(typeof jszip === 'undefined') jszip = require('/aspl_pos_backend_dashboard/static/src/js/libs/jszip/jszip.js');
		_fs = require('fs');
	}
}

function resolve_path(path, base) {
	var result = base.split('/');
	if(base.slice(-1) != "/") result.pop(); // folder path
	var target = path.split('/');
	while (target.length !== 0) {
		var step = target.shift();
		if (step === '..') result.pop();
		else if (step !== '.') result.push(step);
	}
	return result.join('/');
}
var attregexg=/([^"\s?>\/]+)=((?:")([^"]*)(?:")|(?:')([^']*)(?:')|([^'">\s]+))/g;
var tagregex=/<[^>]*>/g;
var nsregex=/<\w*:/, nsregex2 = /<(\/?)\w+:/;
function parsexmltag(tag, skip_root) {
	var z = ({});
	var eq = 0, c = 0;
	for(; eq !== tag.length; ++eq) if((c = tag.charCodeAt(eq)) === 32 || c === 10 || c === 13) break;
	if(!skip_root) z[0] = tag.substr(0, eq);
	if(eq === tag.length) return z;
	var m = tag.match(attregexg), j=0, v="", i=0, q="", cc="", quot = 1;
	if(m) for(i = 0; i != m.length; ++i) {
		cc = m[i];
		for(c=0; c != cc.length; ++c) if(cc.charCodeAt(c) === 61) break;
		q = cc.substr(0,c);
		quot = ((eq=cc.charCodeAt(c+1)) == 34 || eq == 39) ? 1 : 0;
		v = cc.substring(c+1+quot, cc.length-quot);
		for(j=0;j!=q.length;++j) if(q.charCodeAt(j) === 58) break;
		if(j===q.length) {
			if(q.indexOf("_") > 0) q = q.substr(0, q.indexOf("_")); // from ods
			z[q] = v;
		}
		else {
			var k = (j===5 && q.substr(0,5)==="xmlns"?"xmlns":"")+q.substr(j+1);
			if(z[k] && q.substr(j-3,3) == "ext") continue; // from ods
			z[k] = v;
		}
	}
	return z;
}
function strip_ns(x) { return x.replace(nsregex2, "<$1"); }

var encodings = {
	'&quot;': '"',
	'&apos;': "'",
	'&gt;': '>',
	'&lt;': '<',
	'&amp;': '&'
};
var rencoding = evert(encodings);
//var rencstr = "&<>'\"".split("");

// TODO: CP remap (need to read file version to determine OS)
var unescapexml = (function() {
	/* 22.4.2.4 bstr (Basic String) */
	var encregex = /&(?:quot|apos|gt|lt|amp|#x?([\da-fA-F]+));/g, coderegex = /_x([\da-fA-F]{4})_/g;
	return function unescapexml(text) {
		var s = text + '';
		return s.replace(encregex, function($$, $1) { return encodings[$$]||String.fromCharCode(parseInt($1,$$.indexOf("x")>-1?16:10))||$$; }).replace(coderegex,function(m,c) {return String.fromCharCode(parseInt(c,16));});
	};
})();

var decregex=/[&<>'"]/g, charegex = /[\u0000-\u0008\u000b-\u001f]/g;
function escapexml(text, xml){
	var s = text + '';
	return s.replace(decregex, function(y) { return rencoding[y]; }).replace(charegex,function(s) { return "_x" + ("000"+s.charCodeAt(0).toString(16)).slice(-4) + "_";});
}
function escapexmltag(text){ return escapexml(text).replace(/ /g,"_x0020_"); }

var htmlcharegex = /[\u0000-\u001f]/g;
function escapehtml(text){
	var s = text + '';
	return s.replace(decregex, function(y) { return rencoding[y]; }).replace(htmlcharegex,function(s) { return "&#x" + ("000"+s.charCodeAt(0).toString(16)).slice(-4) + ";"; });
}

/* TODO: handle codepages */
var xlml_fixstr = (function() {
	var entregex = /&#(\d+);/g;
	function entrepl($$,$1) { return String.fromCharCode(parseInt($1,10)); }
	return function xlml_fixstr(str) { return str.replace(entregex,entrepl); };
})();
var xlml_unfixstr = (function() {
	return function xlml_unfixstr(str) { return str.replace(/(\r\n|[\r\n])/g,"\&#10;"); };
})();

function parsexmlbool(value, tag) {
	switch(value) {
		case '1': case 'true': case 'TRUE': return true;
		/* case '0': case 'false': case 'FALSE':*/
		default: return false;
	}
}

var utf8read = function utf8reada(orig) {
	var out = "", i = 0, c = 0, d = 0, e = 0, f = 0, w = 0;
	while (i < orig.length) {
		c = orig.charCodeAt(i++);
		if (c < 128) { out += String.fromCharCode(c); continue; }
		d = orig.charCodeAt(i++);
		if (c>191 && c<224) { out += String.fromCharCode(((c & 31) << 6) | (d & 63)); continue; }
		e = orig.charCodeAt(i++);
		if (c < 240) { out += String.fromCharCode(((c & 15) << 12) | ((d & 63) << 6) | (e & 63)); continue; }
		f = orig.charCodeAt(i++);
		w = (((c & 7) << 18) | ((d & 63) << 12) | ((e & 63) << 6) | (f & 63))-65536;
		out += String.fromCharCode(0xD800 + ((w>>>10)&1023));
		out += String.fromCharCode(0xDC00 + (w&1023));
	}
	return out;
};


if(has_buf) {
	var utf8readb = function utf8readb(data) {
		var out = new Buffer(2*data.length), w, i, j = 1, k = 0, ww=0, c;
		for(i = 0; i < data.length; i+=j) {
			j = 1;
			if((c=data.charCodeAt(i)) < 128) w = c;
			else if(c < 224) { w = (c&31)*64+(data.charCodeAt(i+1)&63); j=2; }
			else if(c < 240) { w=(c&15)*4096+(data.charCodeAt(i+1)&63)*64+(data.charCodeAt(i+2)&63); j=3; }
			else { j = 4;
				w = (c & 7)*262144+(data.charCodeAt(i+1)&63)*4096+(data.charCodeAt(i+2)&63)*64+(data.charCodeAt(i+3)&63);
				w -= 65536; ww = 0xD800 + ((w>>>10)&1023); w = 0xDC00 + (w&1023);
			}
			if(ww !== 0) { out[k++] = ww&255; out[k++] = ww>>>8; ww = 0; }
			out[k++] = w%256; out[k++] = w>>>8;
		}
		return out.slice(0,k).toString('ucs2');
	};
	var corpus = "foo bar baz\u00e2\u0098\u0083\u00f0\u009f\u008d\u00a3";
	if(utf8read(corpus) == utf8readb(corpus)) utf8read = utf8readb;
	// $FlowIgnore
	var utf8readc = function utf8readc(data) { return Buffer(data, 'binary').toString('utf8'); };
	if(utf8read(corpus) == utf8readc(corpus)) utf8read = utf8readc;
}

// matches <foo>...</foo> extracts content
var matchtag = (function() {
	var mtcache = ({});
	return function matchtag(f,g) {
		var t = f+"|"+(g||"");
		if(mtcache[t]) return mtcache[t];
		return (mtcache[t] = new RegExp('<(?:\\w+:)?'+f+'(?: xml:space="preserve")?(?:[^>]*)>([^\u2603]*)</(?:\\w+:)?'+f+'>',((g||""))));
	};
})();

var vtregex = (function(){ var vt_cache = {};
	return function vt_regex(bt) {
		if(vt_cache[bt] !== undefined) return vt_cache[bt];
		return (vt_cache[bt] = new RegExp("<(?:vt:)?" + bt + ">(.*?)</(?:vt:)?" + bt + ">", 'g') );
};})();
var vtvregex = /<\/?(?:vt:)?variant>/g, vtmregex = /<(?:vt:)([^>]*)>(.*)</;
function parseVector(data) {
	var h = parsexmltag(data);

	var matches = data.match(vtregex(h.baseType))||[];
	if(matches.length != h.size) throw new Error("unexpected vector length " + matches.length + " != " + h.size);
	var res = [];
	matches.forEach(function(x) {
		var v = x.replace(vtvregex,"").match(vtmregex);
		res.push({v:utf8read(v[2]), t:v[1]});
	});
	return res;
}

var wtregex = /(^\s|\s$|\n)/;
function writetag(f,g) {return '<' + f + (g.match(wtregex)?' xml:space="preserve"' : "") + '>' + g + '</' + f + '>';}

function wxt_helper(h) { return keys(h).map(function(k) { return " " + k + '="' + h[k] + '"';}).join(""); }
function writextag(f,g,h) { return '<' + f + (isval(h) ? wxt_helper(h) : "") + (isval(g) ? (g.match(wtregex)?' xml:space="preserve"' : "") + '>' + g + '</' + f : "/") + '>';}

function write_w3cdtf(d, t) { try { return d.toISOString().replace(/\.\d*/,""); } catch(e) { if(t) throw e; } return ""; }

function write_vt(s) {
	switch(typeof s) {
		case 'string': return writextag('vt:lpwstr', s);
		case 'number': return writextag((s|0)==s?'vt:i4':'vt:r8', String(s));
		case 'boolean': return writextag('vt:bool',s?'true':'false');
	}
	if(s instanceof Date) return writextag('vt:filetime', write_w3cdtf(s));
	throw new Error("Unable to serialize " + s);
}

var XML_HEADER = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n';
var XMLNS = ({
	'dc': 'http://purl.org/dc/elements/1.1/',
	'dcterms': 'http://purl.org/dc/terms/',
	'dcmitype': 'http://purl.org/dc/dcmitype/',
	'mx': 'http://schemas.microsoft.com/office/mac/excel/2008/main',
	'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
	'sjs': 'http://schemas.openxmlformats.org/package/2006/sheetjs/core-properties',
	'vt': 'http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes',
	'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
	'xsd': 'http://www.w3.org/2001/XMLSchema'
});

XMLNS.main = [
	'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
	'http://purl.oclc.org/ooxml/spreadsheetml/main',
	'http://schemas.microsoft.com/office/excel/2006/main',
	'http://schemas.microsoft.com/office/excel/2006/2'
];

var XLMLNS = ({
	'o':    'urn:schemas-microsoft-com:office:office',
	'x':    'urn:schemas-microsoft-com:office:excel',
	'ss':   'urn:schemas-microsoft-com:office:spreadsheet',
	'dt':   'uuid:C2F41010-65B3-11d1-A29F-00AA00C14882',
	'mv':   'http://macVmlSchemaUri',
	'v':    'urn:schemas-microsoft-com:vml',
	'html': 'http://www.w3.org/TR/REC-html40'
});
function read_double_le(b, idx) {
	var s = 1 - 2 * (b[idx + 7] >>> 7);
	var e = ((b[idx + 7] & 0x7f) << 4) + ((b[idx + 6] >>> 4) & 0x0f);
	var m = (b[idx+6]&0x0f);
	for(var i = 5; i >= 0; --i) m = m * 256 + b[idx + i];
	if(e == 0x7ff) return m == 0 ? s * Infinity : NaN;
	if(e == 0) e = -1022;
	else { e -= 1023; m += Math.pow(2,52); }
	return s * Math.pow(2, e - 52) * m;
}

function write_double_le(b, v, idx) {
	var bs = ((v < 0 || 1/v == -Infinity) ? 1 : 0) << 7, e = 0, m = 0;
	var av = bs ? -v : v;
	if(!isFinite(av)) { e = 0x7ff; m = isNaN(v) ? 0x6969 : 0; }
	else {
		e = Math.floor(Math.log(av) * Math.LOG2E);
		m = v * Math.pow(2, 52 - e);
		if(e <= -1023 && (!isFinite(m) || m < Math.pow(2,52))) { e = -1022; }
		else { m -= Math.pow(2,52); e+=1023; }
	}
	for(var i = 0; i <= 5; ++i, m/=256) b[idx + i] = m & 0xff;
	b[idx + 6] = ((e & 0x0f) << 4) | m & 0xf;
	b[idx + 7] = (e >> 4) | bs;
}

var __toBuffer, ___toBuffer;
__toBuffer = ___toBuffer = function toBuffer_(bufs) { var x = []; for(var i = 0; i < bufs[0].length; ++i) { x.push.apply(x, bufs[0][i]); } return x; };
var __utf16le, ___utf16le;
__utf16le = ___utf16le = function utf16le_(b,s,e) { var ss=[]; for(var i=s; i<e; i+=2) ss.push(String.fromCharCode(__readUInt16LE(b,i))); return ss.join(""); };
var __hexlify, ___hexlify;
__hexlify = ___hexlify = function hexlify_(b,s,l) { return b.slice(s,(s+l)).map(function(x){return (x<16?"0":"") + x.toString(16);}).join(""); };
var __utf8, ___utf8;
__utf8 = ___utf8 = function(b,s,e) { var ss=[]; for(var i=s; i<e; i++) ss.push(String.fromCharCode(__readUInt8(b,i))); return ss.join(""); };
var __lpstr, ___lpstr;
__lpstr = ___lpstr = function lpstr_(b,i) { var len = __readUInt32LE(b,i); return len > 0 ? __utf8(b, i+4,i+4+len-1) : "";};
var __lpwstr, ___lpwstr;
__lpwstr = ___lpwstr = function lpwstr_(b,i) { var len = 2*__readUInt32LE(b,i); return len > 0 ? __utf8(b, i+4,i+4+len-1) : "";};
var __lpp4, ___lpp4;
__lpp4 = ___lpp4 = function lpp4_(b,i) { var len = __readUInt32LE(b,i); return len > 0 ? __utf16le(b, i+4,i+4+len) : "";};
var __8lpp4, ___8lpp4;
__8lpp4 = ___8lpp4 = function lpp4_8(b,i) { var len = __readUInt32LE(b,i); return len > 0 ? __utf8(b, i+4,i+4+len) : "";};
var __double, ___double;
__double = ___double = function(b, idx) { return read_double_le(b, idx);};

var is_buf = function is_buf_a(a) { return Array.isArray(a); };
if(has_buf) {
	__utf16le = function utf16le_b(b,s,e) { if(!Buffer.isBuffer(b)) return ___utf16le(b,s,e); return b.toString('utf16le',s,e); };
	__hexlify = function(b,s,l) { return Buffer.isBuffer(b) ? b.toString('hex',s,s+l) : ___hexlify(b,s,l); };
	__lpstr = function lpstr_b(b,i) { if(!Buffer.isBuffer(b)) return ___lpstr(b, i); var len = b.readUInt32LE(i); return len > 0 ? b.toString('utf8',i+4,i+4+len-1) : "";};
	__lpwstr = function lpwstr_b(b,i) { if(!Buffer.isBuffer(b)) return ___lpwstr(b, i); var len = 2*b.readUInt32LE(i); return b.toString('utf16le',i+4,i+4+len-1);};
	__lpp4 = function lpp4_b(b,i) { if(!Buffer.isBuffer(b)) return ___lpp4(b, i); var len = b.readUInt32LE(i); return b.toString('utf16le',i+4,i+4+len);};
	__8lpp4 = function lpp4_8b(b,i) { if(!Buffer.isBuffer(b)) return ___8lpp4(b, i); var len = b.readUInt32LE(i); return b.toString('utf8',i+4,i+4+len);};
	__utf8 = function utf8_b(b, s,e) { return b.toString('utf8',s,e); };
	__toBuffer = function(bufs) { return (bufs[0].length > 0 && Buffer.isBuffer(bufs[0][0])) ? Buffer.concat(bufs[0]) : ___toBuffer(bufs);};
	bconcat = function(bufs) { return Buffer.isBuffer(bufs[0]) ? Buffer.concat(bufs) : [].concat.apply([], bufs); };
	__double = function double_(b,i) { if(Buffer.isBuffer(b)) return b.readDoubleLE(i); return ___double(b,i); };
	is_buf = function is_buf_b(a) { return Buffer.isBuffer(a) || Array.isArray(a); };
}

/* from js-xls */
if(typeof cptable !== 'undefined') {
	__utf16le = function(b,s,e) { return cptable.utils.decode(1200, b.slice(s,e)); };
	__utf8 = function(b,s,e) { return cptable.utils.decode(65001, b.slice(s,e)); };
	__lpstr = function(b,i) { var len = __readUInt32LE(b,i); return len > 0 ? cptable.utils.decode(current_codepage, b.slice(i+4, i+4+len-1)) : "";};
	__lpwstr = function(b,i) { var len = 2*__readUInt32LE(b,i); return len > 0 ? cptable.utils.decode(1200, b.slice(i+4,i+4+len-1)) : "";};
	__lpp4 = function(b,i) { var len = __readUInt32LE(b,i); return len > 0 ? cptable.utils.decode(1200, b.slice(i+4,i+4+len)) : "";};
	__8lpp4 = function(b,i) { var len = __readUInt32LE(b,i); return len > 0 ? cptable.utils.decode(65001, b.slice(i+4,i+4+len)) : "";};
}

var __readUInt8 = function(b, idx) { return b[idx]; };
var __readUInt16LE = function(b, idx) { return b[idx+1]*(1<<8)+b[idx]; };
var __readInt16LE = function(b, idx) { var u = b[idx+1]*(1<<8)+b[idx]; return (u < 0x8000) ? u : (0xffff - u + 1) * -1; };
var __readUInt32LE = function(b, idx) { return b[idx+3]*(1<<24)+(b[idx+2]<<16)+(b[idx+1]<<8)+b[idx]; };
var __readInt32LE = function(b, idx) { return (b[idx+3]<<24)|(b[idx+2]<<16)|(b[idx+1]<<8)|b[idx]; };

var ___unhexlify = function(s) { return s.match(/../g).map(function(x) { return parseInt(x,16);}); };
var __unhexlify = typeof Buffer !== "undefined" ? function(s) { return Buffer.isBuffer(s) ? new Buffer(s, 'hex') : ___unhexlify(s); } : ___unhexlify;

function ReadShift(size, t) {
	var o="", oI, oR, oo=[], w, vv, i, loc;
	switch(t) {
		case 'dbcs':
			loc = this.l;
			if(has_buf && Buffer.isBuffer(this)) o = this.slice(this.l, this.l+2*size).toString("utf16le");
			else for(i = 0; i != size; ++i) { o+=String.fromCharCode(__readUInt16LE(this, loc)); loc+=2; }
			size *= 2;
			break;

		case 'utf8': o = __utf8(this, this.l, this.l + size); break;
		case 'utf16le': size *= 2; o = __utf16le(this, this.l, this.l + size); break;

		case 'wstr':
			if(typeof cptable !== 'undefined') o = cptable.utils.decode(current_codepage, this.slice(this.l, this.l+2*size));
			else return ReadShift.call(this, size, 'dbcs');
			size = 2 * size; break;

		/* [MS-OLEDS] 2.1.4 LengthPrefixedAnsiString */
		case 'lpstr': o = __lpstr(this, this.l); size = 5 + o.length; break;
		/* [MS-OLEDS] 2.1.5 LengthPrefixedUnicodeString */
		case 'lpwstr': o = __lpwstr(this, this.l); size = 5 + o.length; if(o[o.length-1] == '\u0000') size += 2; break;
		/* [MS-OFFCRYPTO] 2.1.2 Length-Prefixed Padded Unicode String (UNICODE-LP-P4) */
		case 'lpp4': size = 4 +  __readUInt32LE(this, this.l); o = __lpp4(this, this.l); if(size & 0x02) size += 2; break;
		/* [MS-OFFCRYPTO] 2.1.3 Length-Prefixed UTF-8 String (UTF-8-LP-P4) */
		case '8lpp4': size = 4 +  __readUInt32LE(this, this.l); o = __8lpp4(this, this.l); if(size & 0x03) size += 4 - (size & 0x03); break;

		case 'cstr': size = 0; o = "";
			while((w=__readUInt8(this, this.l + size++))!==0) oo.push(_getchar(w));
			o = oo.join(""); break;
		case '_wstr': size = 0; o = "";
			while((w=__readUInt16LE(this,this.l +size))!==0){oo.push(_getchar(w));size+=2;}
			size+=2; o = oo.join(""); break;

		/* sbcs and dbcs support continue records in the SST way TODO codepages */
		case 'dbcs-cont': o = ""; loc = this.l;
			for(i = 0; i != size; ++i) {
				if(this.lens && this.lens.indexOf(loc) !== -1) {
					w = __readUInt8(this, loc);
					this.l = loc + 1;
					vv = ReadShift.call(this, size-i, w ? 'dbcs-cont' : 'sbcs-cont');
					return oo.join("") + vv;
				}
				oo.push(_getchar(__readUInt16LE(this, loc)));
				loc+=2;
			} o = oo.join(""); size *= 2; break;

		case 'sbcs-cont': o = ""; loc = this.l;
			for(i = 0; i != size; ++i) {
				if(this.lens && this.lens.indexOf(loc) !== -1) {
					w = __readUInt8(this, loc);
					this.l = loc + 1;
					vv = ReadShift.call(this, size-i, w ? 'dbcs-cont' : 'sbcs-cont');
					return oo.join("") + vv;
				}
				oo.push(_getchar(__readUInt8(this, loc)));
				loc+=1;
			} o = oo.join(""); break;

		default:
	switch(size) {
		case 1: oI = __readUInt8(this, this.l); this.l++; return oI;
		case 2: oI = (t === 'i' ? __readInt16LE : __readUInt16LE)(this, this.l); this.l += 2; return oI;
		case 4:
			if(t === 'i' || (this[this.l+3] & 0x80)===0) { oI = __readInt32LE(this, this.l); this.l += 4; return oI; }
			else { oR = __readUInt32LE(this, this.l); this.l += 4; } return oR;
		case 8: if(t === 'f') { oR = __double(this, this.l); this.l += 8; return oR; }
		/* falls through */
		case 16: o = __hexlify(this, this.l, size); break;
	}}
	this.l+=size; return o;
}

var __writeUInt16LE = function(b, val, idx) { b[idx] = (val & 0xFF); b[idx+1] = ((val >>> 8) & 0xFF); };
var __writeUInt32LE = function(b, val, idx) { b[idx] = (val & 0xFF); b[idx+1] = ((val >>> 8) & 0xFF); b[idx+2] = ((val >>> 16) & 0xFF); b[idx+3] = ((val >>> 24) & 0xFF); };
var __writeInt32LE  = function(b, val, idx) { b[idx] = (val & 0xFF); b[idx+1] = ((val >> 8) & 0xFF); b[idx+2] = ((val >> 16) & 0xFF); b[idx+3] = ((val >> 24) & 0xFF); };

function WriteShift(t, val, f) {
	var size = 0, i = 0;
	if(f === 'dbcs') {
for(i = 0; i != val.length; ++i) __writeUInt16LE(this, val.charCodeAt(i), this.l + 2 * i);
		size = 2 * val.length;
	} else if(f === 'sbcs') {
for(i = 0; i != val.length; ++i) this[this.l + i] = val.charCodeAt(i) & 0xFF;
		size = val.length;
	} else  switch(t) {
		case  1: size = 1; this[this.l] = val&0xFF; break;
		case  2: size = 2; this[this.l] = val&0xFF; val >>>= 8; this[this.l+1] = val&0xFF; break;
		case  3: size = 3; this[this.l] = val&0xFF; val >>>= 8; this[this.l+1] = val&0xFF; val >>>= 8; this[this.l+2] = val&0xFF; break;
		case  4: size = 4; __writeUInt32LE(this, val, this.l); break;
		case  8: size = 8; if(f === 'f') { write_double_le(this, val, this.l); break; }
		/* falls through */
		case 16: break;
		case -4: size = 4; __writeInt32LE(this, val, this.l); break;
	}
	this.l += size; return this;
}

function CheckField(hexstr, fld) {
	var m = __hexlify(this,this.l,hexstr.length>>1);
	if(m !== hexstr) throw fld + 'Expected ' + hexstr + ' saw ' + m;
	this.l += hexstr.length>>1;
}

function prep_blob(blob, pos) {
	blob.l = pos;
	blob.read_shift = ReadShift;
	blob.chk = CheckField;
	blob.write_shift = WriteShift;
}

function parsenoop(blob, length) { blob.l += length; }
function parsenooplog(blob, length) { if(typeof console != 'undefined') console.log(blob.slice(blob.l, blob.l + length)); blob.l += length; }

function writenoop(blob, length) { blob.l += length; }

function new_buf(sz) {
	var o = new_raw_buf(sz);
	prep_blob(o, 0);
	return o;
}

/* [MS-XLSB] 2.1.4 Record */
function recordhopper(data, cb, opts) {
	if(!data) return;
	var tmpbyte, cntbyte, length;
	prep_blob(data, data.l || 0);
	var L = data.length, RT = 0, tgt = 0;
	while(data.l < L) {
		RT = data.read_shift(1);
		if(RT & 0x80) RT = (RT & 0x7F) + ((data.read_shift(1) & 0x7F)<<7);
		var R = XLSBRecordEnum[RT] || XLSBRecordEnum[0xFFFF];
		tmpbyte = data.read_shift(1);
		length = tmpbyte & 0x7F;
		for(cntbyte = 1; cntbyte <4 && (tmpbyte & 0x80); ++cntbyte) length += ((tmpbyte = data.read_shift(1)) & 0x7F)<<(7*cntbyte);
		tgt = data.l + length;
		var d = R.f(data, length, opts);
		data.l = tgt;
		if(cb(d, R.n, RT)) return;
	}
}

/* control buffer usage for fixed-length buffers */
function buf_array() {
	var bufs = [], blksz = 2048;
	var newblk = function ba_newblk(sz) {
		var o = (new_buf(sz));
		prep_blob(o, 0);
		return o;
	};

	var curbuf = newblk(blksz);

	var endbuf = function ba_endbuf() {
		if(!curbuf) return;
		if(curbuf.length > curbuf.l) curbuf = curbuf.slice(0, curbuf.l);
		if(curbuf.length > 0) bufs.push(curbuf);
		curbuf = null;
	};

	var next = function ba_next(sz) {
		if(curbuf && sz < curbuf.length - curbuf.l) return curbuf;
		endbuf();
		return (curbuf = newblk(Math.max(sz+1, blksz)));
	};

	var end = function ba_end() {
		endbuf();
		return __toBuffer([bufs]);
	};

	var push = function ba_push(buf) { endbuf(); curbuf = buf; next(blksz); };

	return ({ next:next, push:push, end:end, _bufs:bufs });
}

function write_record(ba, type, payload, length) {
	var t = Number(evert_RE[type]), l;
	if(isNaN(t)) return; // TODO: throw something here?
	if(!length) length = XLSBRecordEnum[t].p || (payload||[]).length || 0;
	l = 1 + (t >= 0x80 ? 1 : 0) + 1 + length;
	if(length >= 0x80) ++l; if(length >= 0x4000) ++l; if(length >= 0x200000) ++l;
	var o = ba.next(l);
	if(t <= 0x7F) o.write_shift(1, t);
	else {
		o.write_shift(1, (t & 0x7F) + 0x80);
		o.write_shift(1, (t >> 7));
	}
	for(var i = 0; i != 4; ++i) {
		if(length >= 0x80) { o.write_shift(1, (length & 0x7F)+0x80); length >>= 7; }
		else { o.write_shift(1, length); break; }
	}
	if(length > 0 && is_buf(payload)) ba.push(payload);
}
/* XLS ranges enforced */
function shift_cell_xls(cell, tgt, opts) {
	var out = dup(cell);
	if(tgt.s) {
		if(out.cRel) out.c += tgt.s.c;
		if(out.rRel) out.r += tgt.s.r;
	} else {
		out.c += tgt.c;
		out.r += tgt.r;
	}
	if(!opts || opts.biff < 12) {
		while(out.c >= 0x100) out.c -= 0x100;
		while(out.r >= 0x10000) out.r -= 0x10000;
	}
	return out;
}

function shift_range_xls(cell, range, opts) {
	var out = dup(cell);
	out.s = shift_cell_xls(out.s, range.s, opts);
	out.e = shift_cell_xls(out.e, range.s, opts);
	return out;
}

function encode_cell_xls(c) {
	var s = encode_cell(c);
	if(c.cRel === 0) s = fix_col(s);
	if(c.rRel === 0) s = fix_row(s);
	return s;
}

function encode_range_xls(r, opts) {
	if(r.s.r == 0 && !r.s.rRel) {
		if(r.e.r == opts.biff >= 12 ? 0xFFFFF : 0xFFFF && !r.e.rRel) {
			return (r.s.cRel ? "" : "$") + encode_col(r.s.c) + ":" + (r.e.cRel ? "" : "$") + encode_col(r.e.c);
		}
	}
	if(r.s.c == 0 && !r.s.cRel) {
		if(r.e.c == opts.biff >= 12 ? 0xFFFF : 0xFF && !r.e.cRel) {
			return (r.s.rRel ? "" : "$") + encode_row(r.s.r) + ":" + (r.e.rRel ? "" : "$") + encode_row(r.e.r);
		}
	}
	return encode_cell_xls(r.s) + ":" + encode_cell_xls(r.e);
}
var OFFCRYPTO = {};

var make_offcrypto = function(O, _crypto) {
	var crypto;
	if(typeof _crypto !== 'undefined') crypto = _crypto;
	else if(typeof require !== 'undefined') {
		try { crypto = require('crypto'); }
		catch(e) { crypto = null; }
	}

	O.rc4 = function(key, data) {
		var S = new Array(256);
		var c = 0, i = 0, j = 0, t = 0;
		for(i = 0; i != 256; ++i) S[i] = i;
		for(i = 0; i != 256; ++i) {
			j = (j + S[i] + (key[i%key.length]).charCodeAt(0))&255;
			t = S[i]; S[i] = S[j]; S[j] = t;
		}
		// $FlowIgnore
		i = j = 0; var out = Buffer(data.length);
		for(c = 0; c != data.length; ++c) {
			i = (i + 1)&255;
			j = (j + S[i])%256;
			t = S[i]; S[i] = S[j]; S[j] = t;
			out[c] = (data[c] ^ S[(S[i]+S[j])&255]);
		}
		return out;
	};

	O.md5 = function(hex) {
		if(!crypto) throw new Error("Unsupported crypto");
		return crypto.createHash('md5').update(hex).digest('hex');
	};
};
/*global crypto:true */
make_offcrypto(OFFCRYPTO, typeof crypto !== "undefined" ? crypto : undefined);

function decode_row(rowstr) { return parseInt(unfix_row(rowstr),10) - 1; }
function encode_row(row) { return "" + (row + 1); }
function fix_row(cstr) { return cstr.replace(/([A-Z]|^)(\d+)$/,"$1$$$2"); }
function unfix_row(cstr) { return cstr.replace(/\$(\d+)$/,"$1"); }

function decode_col(colstr) { var c = unfix_col(colstr), d = 0, i = 0; for(; i !== c.length; ++i) d = 26*d + c.charCodeAt(i) - 64; return d - 1; }
function encode_col(col) { var s=""; for(++col; col; col=Math.floor((col-1)/26)) s = String.fromCharCode(((col-1)%26) + 65) + s; return s; }
function fix_col(cstr) { return cstr.replace(/^([A-Z])/,"$$$1"); }
function unfix_col(cstr) { return cstr.replace(/^\$([A-Z])/,"$1"); }

function split_cell(cstr) { return cstr.replace(/(\$?[A-Z]*)(\$?\d*)/,"$1,$2").split(","); }
function decode_cell(cstr) { var splt = split_cell(cstr); return { c:decode_col(splt[0]), r:decode_row(splt[1]) }; }
function encode_cell(cell) { return encode_col(cell.c) + encode_row(cell.r); }
function fix_cell(cstr) { return fix_col(fix_row(cstr)); }
function unfix_cell(cstr) { return unfix_col(unfix_row(cstr)); }
function decode_range(range) { var x =range.split(":").map(decode_cell); return {s:x[0],e:x[x.length-1]}; }
function encode_range(cs,ce) {
	if(typeof ce === 'undefined' || typeof ce === 'number') {
return encode_range(cs.s, cs.e);
	}
if(typeof cs !== 'string') cs = encode_cell((cs));
	if(typeof ce !== 'string') ce = encode_cell((ce));
return cs == ce ? cs : cs + ":" + ce;
}

function safe_decode_range(range) {
	var o = {s:{c:0,r:0},e:{c:0,r:0}};
	var idx = 0, i = 0, cc = 0;
	var len = range.length;
	for(idx = 0; i < len; ++i) {
		if((cc=range.charCodeAt(i)-64) < 1 || cc > 26) break;
		idx = 26*idx + cc;
	}
	o.s.c = --idx;

	for(idx = 0; i < len; ++i) {
		if((cc=range.charCodeAt(i)-48) < 0 || cc > 9) break;
		idx = 10*idx + cc;
	}
	o.s.r = --idx;

	if(i === len || range.charCodeAt(++i) === 58) { o.e.c=o.s.c; o.e.r=o.s.r; return o; }

	for(idx = 0; i != len; ++i) {
		if((cc=range.charCodeAt(i)-64) < 1 || cc > 26) break;
		idx = 26*idx + cc;
	}
	o.e.c = --idx;

	for(idx = 0; i != len; ++i) {
		if((cc=range.charCodeAt(i)-48) < 0 || cc > 9) break;
		idx = 10*idx + cc;
	}
	o.e.r = --idx;
	return o;
}

function safe_format_cell(cell, v) {
	var q = (cell.t == 'd' && v instanceof Date);
	if(cell.z != null) try { return (cell.w = SSF.format(cell.z, q ? datenum(v) : v)); } catch(e) { }
	try { return (cell.w = SSF.format((cell.XF||{}).ifmt||(q ? 14 : 0),  q ? datenum(v) : v)); } catch(e) { return ''+v; }
}

function format_cell(cell, v, o) {
	if(cell == null || cell.t == null || cell.t == 'z') return "";
	if(cell.w !== undefined) return cell.w;
	if(cell.t == 'd' && !cell.z && o && o.dateNF) cell.z = o.dateNF;
	if(v == undefined) return safe_format_cell(cell, cell.v, o);
	return safe_format_cell(cell, v, o);
}

function sheet_to_workbook(sheet, opts) {
	var n = opts && opts.sheet ? opts.sheet : "Sheet1";
	var sheets = {}; sheets[n] = sheet;
	return { SheetNames: [n], Sheets: sheets };
}

function aoa_to_sheet(data, opts) {
	var o = opts || {};
	if(DENSE != null && o.dense == null) o.dense = DENSE;
	var ws = o.dense ? ([]) : ({});
	var range = ({s: {c:10000000, r:10000000}, e: {c:0, r:0}});
	for(var R = 0; R != data.length; ++R) {
		for(var C = 0; C != data[R].length; ++C) {
			if(typeof data[R][C] === 'undefined') continue;
			var cell = ({v: data[R][C] });
			if(Array.isArray(cell.v)) { cell.f = data[R][C][1]; cell.v = cell.v[0]; }
			if(range.s.r > R) range.s.r = R;
			if(range.s.c > C) range.s.c = C;
			if(range.e.r < R) range.e.r = R;
			if(range.e.c < C) range.e.c = C;
			if(cell.v === null) { if(cell.f) cell.t = 'n'; else if(!o.cellStubs) continue; else cell.t = 'z'; }
			else if(typeof cell.v === 'number') cell.t = 'n';
			else if(typeof cell.v === 'boolean') cell.t = 'b';
			else if(cell.v instanceof Date) {
				cell.z = o.dateNF || SSF._table[14];
				if(o.cellDates) { cell.t = 'd'; cell.w = SSF.format(cell.z, datenum(cell.v)); }
				else { cell.t = 'n'; cell.v = datenum(cell.v); cell.w = SSF.format(cell.z, cell.v); }
			}
			else cell.t = 's';
			if(o.dense) {
				if(!ws[R]) ws[R] = [];
				ws[R][C] = cell;
			} else {
				var cell_ref = encode_cell(({c:C,r:R}));
				ws[cell_ref] = cell;
			}
		}
	}
	if(range.s.c < 10000000) ws['!ref'] = encode_range(range);
	return ws;
}

function write_UInt32LE(x, o) {
	if(!o) o = new_buf(4);
	o.write_shift(4, x);
	return o;
}

/* [MS-XLSB] 2.5.168 */
function parse_XLWideString(data) {
	var cchCharacters = data.read_shift(4);
	return cchCharacters === 0 ? "" : data.read_shift(cchCharacters, 'dbcs');
}
function write_XLWideString(data, o) {
	var _null = false; if(o == null) { _null = true; o = new_buf(4+2*data.length); }
	o.write_shift(4, data.length);
	if(data.length > 0) o.write_shift(0, data, 'dbcs');
	return _null ? o.slice(0, o.l) : o;
}

/* [MS-XLSB] 2.5.143 */
function parse_StrRun(data, length) {
	return { ich: data.read_shift(2), ifnt: data.read_shift(2) };
}
function write_StrRun(run, o) {
	if(!o) o = new_buf(4);
	o.write_shift(2, run.ich || 0);
	o.write_shift(2, run.ifnt || 0);
	return o;
}

/* [MS-XLSB] 2.1.7.121 */
function parse_RichStr(data, length) {
	var start = data.l;
	var flags = data.read_shift(1);
	var str = parse_XLWideString(data);
	var rgsStrRun = [];
	var z = ({ t: str, h: str });
	if((flags & 1) !== 0) { /* fRichStr */
		/* TODO: formatted string */
		var dwSizeStrRun = data.read_shift(4);
		for(var i = 0; i != dwSizeStrRun; ++i) rgsStrRun.push(parse_StrRun(data));
		z.r = rgsStrRun;
	}
	else z.r = [{ich:0, ifnt:0}];
	//if((flags & 2) !== 0) { /* fExtStr */
	//	/* TODO: phonetic string */
	//}
	data.l = start + length;
	return z;
}
function write_RichStr(str, o) {
	/* TODO: formatted string */
	var _null = false; if(o == null) { _null = true; o = new_buf(15+4*str.t.length); }
	o.write_shift(1,0);
	write_XLWideString(str.t, o);
	return _null ? o.slice(0, o.l) : o;
}
/* [MS-XLSB] 2.4.325 BrtCommentText (RichStr w/1 run) */
var parse_BrtCommentText = parse_RichStr;
function write_BrtCommentText(str, o) {
	/* TODO: formatted string */
	var _null = false; if(o == null) { _null = true; o = new_buf(23+4*str.t.length); }
	o.write_shift(1,1);
	write_XLWideString(str.t, o);
	o.write_shift(4,1);
	write_StrRun({ich:0,ifnt:0}, o);
	return _null ? o.slice(0, o.l) : o;
}

/* [MS-XLSB] 2.5.9 */
function parse_XLSBCell(data) {
	var col = data.read_shift(4);
	var iStyleRef = data.read_shift(2);
	iStyleRef += data.read_shift(1) <<16;
	var fPhShow = data.read_shift(1);
	return { c:col, iStyleRef: iStyleRef };
}
function write_XLSBCell(cell, o) {
	if(o == null) o = new_buf(8);
	o.write_shift(-4, cell.c);
	o.write_shift(3, cell.iStyleRef || cell.s);
	o.write_shift(1, 0); /* fPhShow */
	return o;
}


/* [MS-XLSB] 2.5.21 */
var parse_XLSBCodeName = parse_XLWideString;
var write_XLSBCodeName = write_XLWideString;

/* [MS-XLSB] 2.5.166 */
function parse_XLNullableWideString(data) {
	var cchCharacters = data.read_shift(4);
	return cchCharacters === 0 || cchCharacters === 0xFFFFFFFF ? "" : data.read_shift(cchCharacters, 'dbcs');
}
function write_XLNullableWideString(data, o) {
	var _null = false; if(o == null) { _null = true; o = new_buf(127); }
	o.write_shift(4, data.length > 0 ? data.length : 0xFFFFFFFF);
	if(data.length > 0) o.write_shift(0, data, 'dbcs');
	return _null ? o.slice(0, o.l) : o;
}

/* [MS-XLSB] 2.5.165 */
var parse_XLNameWideString = parse_XLWideString;
var write_XLNameWideString = write_XLWideString;

/* [MS-XLSB] 2.5.114 */
var parse_RelID = parse_XLNullableWideString;
var write_RelID = write_XLNullableWideString;


/* [MS-XLSB] 2.5.122 */
/* [MS-XLS] 2.5.217 */
function parse_RkNumber(data) {
	var b = data.slice(data.l, data.l+4);
	var fX100 = b[0] & 1, fInt = b[0] & 2;
	data.l+=4;
	b[0] &= 0xFC; // b[0] &= ~3;
	var RK = fInt === 0 ? __double([0,0,0,0,b[0],b[1],b[2],b[3]],0) : __readInt32LE(b,0)>>2;
	return fX100 ? RK/100 : RK;
}
function write_RkNumber(data, o) {
	if(o == null) o = new_buf(4);
	var fX100 = 0, fInt = 0, d100 = data * 100;
	if(data == (data | 0) && data >= -(1<<29) && data < (1 << 29)) { fInt = 1; }
	else if(d100 == (d100 | 0) && d100 >= -(1<<29) && d100 < (1 << 29)) { fInt = 1; fX100 = 1; }
	if(fInt) o.write_shift(-4, ((fX100 ? d100 : data) << 2) + (fX100 + 2));
	else throw new Error("unsupported RkNumber " + data); // TODO
}


/* [MS-XLSB] 2.5.117 RfX */
function parse_RfX(data) {
	var cell = ({s: {}, e: {}});
	cell.s.r = data.read_shift(4);
	cell.e.r = data.read_shift(4);
	cell.s.c = data.read_shift(4);
	cell.e.c = data.read_shift(4);
	return cell;
}

function write_RfX(r, o) {
	if(!o) o = new_buf(16);
	o.write_shift(4, r.s.r);
	o.write_shift(4, r.e.r);
	o.write_shift(4, r.s.c);
	o.write_shift(4, r.e.c);
	return o;
}

/* [MS-XLSB] 2.5.153 UncheckedRfX */
var parse_UncheckedRfX = parse_RfX;
var write_UncheckedRfX = write_RfX;

/* [MS-XLSB] 2.5.171 */
/* [MS-XLS] 2.5.342 */
/* TODO: error checking, NaN and Infinity values are not valid Xnum */
function parse_Xnum(data, length) { return data.read_shift(8, 'f'); }
function write_Xnum(data, o) { return (o || new_buf(8)).write_shift(8, data, 'f'); }

/* [MS-XLSB] 2.5.198.2 */
var BErr = {
0x00: "#NULL!",
0x07: "#DIV/0!",
0x0F: "#VALUE!",
0x17: "#REF!",
0x1D: "#NAME?",
0x24: "#NUM!",
0x2A: "#N/A",
0x2B: "#GETTING_DATA",
0xFF: "#WTF?"
};
var RBErr = evert_num(BErr);

/* [MS-XLSB] 2.4.321 BrtColor */
function parse_BrtColor(data, length) {
	var out = {};
	var d = data.read_shift(1);

	var fValidRGB = d & 1;
	var xColorType = d >>> 1;

	var index = data.read_shift(1);
	var nTS = data.read_shift(2, 'i');
	var bR = data.read_shift(1);
	var bG = data.read_shift(1);
	var bB = data.read_shift(1);
	var bAlpha = data.read_shift(1);

	switch(xColorType) {
		case 0: out.auto = 1; break;
		case 1:
			out.index = index;
			var icv = XLSIcv[index];
			/* automatic pseudo index 81 */
			if(icv) out.rgb = icv[0].toString(16) + icv[1].toString(16) + icv[2].toString(16);
			break;
		case 2:
			/* if(!fValidRGB) throw new Error("invalid"); */
			out.rgb = bR.toString(16) + bG.toString(16) + bB.toString(16);
			break;
		case 3: out.theme = index; break;
	}
	if(nTS != 0) out.tint = nTS > 0 ? nTS / 32767 : nTS / 32768;

	return out;
}
function write_BrtColor(color, o) {
	if(!o) o = new_buf(8);
	if(!color||color.auto) { o.write_shift(4, 0); o.write_shift(4, 0); return o; }
	if(color.index) {
		o.write_shift(1, 0x02);
		o.write_shift(1, color.index);
	} else if(color.theme) {
		o.write_shift(1, 0x06);
		o.write_shift(1, color.theme);
	} else {
		o.write_shift(1, 0x05);
		o.write_shift(1, 0);
	}
	var nTS = color.tint || 0;
	if(nTS > 0) nTS *= 32767;
	else if(nTS < 0) nTS *= 32768;
	o.write_shift(2, nTS);
	if(!color.rgb) {
		o.write_shift(2, 0);
		o.write_shift(1, 0);
		o.write_shift(1, 0);
	} else {
		var rgb = (color.rgb || 'FFFFFF');
		o.write_shift(1, parseInt(rgb.substr(0,2),16));
		o.write_shift(1, parseInt(rgb.substr(2,2),16));
		o.write_shift(1, parseInt(rgb.substr(4,2),16));
		o.write_shift(1, 0xFF);
	}
	return o;
}

/* [MS-XLSB] 2.5.52 */
function parse_FontFlags(data, length, opts) {
	var d = data.read_shift(1);
	data.l++;
	var out = {
		/* fBold: d & 0x01 */
		fItalic: d & 0x02,
		/* fUnderline: d & 0x04 */
		fStrikeout: d & 0x08,
		fOutline: d & 0x10,
		fShadow: d & 0x20,
		fCondense: d & 0x40,
		fExtend: d & 0x80
	};
	return out;
}
function write_FontFlags(font, o) {
	if(!o) o = new_buf(2);
	var grbit =
		(font.italic   ? 0x02 : 0) |
		(font.strike   ? 0x08 : 0) |
		(font.outline  ? 0x10 : 0) |
		(font.shadow   ? 0x20 : 0) |
		(font.condense ? 0x40 : 0) |
		(font.extend   ? 0x80 : 0);
	o.write_shift(1, grbit);
	o.write_shift(1, 0);
	return o;
}

/* [MS-OLEPS] 2.2 PropertyType */
{
	//var VT_EMPTY    = 0x0000;
	//var VT_NULL     = 0x0001;
	var VT_I2       = 0x0002;
	var VT_I4       = 0x0003;
	//var VT_R4       = 0x0004;
	//var VT_R8       = 0x0005;
	//var VT_CY       = 0x0006;
	//var VT_DATE     = 0x0007;
	//var VT_BSTR     = 0x0008;
	//var VT_ERROR    = 0x000A;
	var VT_BOOL     = 0x000B;
	var VT_VARIANT  = 0x000C;
	//var VT_DECIMAL  = 0x000E;
	//var VT_I1       = 0x0010;
	//var VT_UI1      = 0x0011;
	//var VT_UI2      = 0x0012;
	var VT_UI4      = 0x0013;
	//var VT_I8       = 0x0014;
	var VT_UI8      = 0x0015;
	//var VT_INT      = 0x0016;
	//var VT_UINT     = 0x0017;
	var VT_LPSTR    = 0x001E;
	//var VT_LPWSTR   = 0x001F;
	var VT_FILETIME = 0x0040;
	//var VT_BLOB     = 0x0041;
	//var VT_STREAM   = 0x0042;
	//var VT_STORAGE  = 0x0043;
	//var VT_STREAMED_Object  = 0x0044;
	//var VT_STORED_Object    = 0x0045;
	//var VT_BLOB_Object      = 0x0046;
	var VT_CF       = 0x0047;
	//var VT_CLSID    = 0x0048;
	//var VT_VERSIONED_STREAM = 0x0049;
	var VT_VECTOR   = 0x1000;
	//var VT_ARRAY    = 0x2000;

	var VT_STRING   = 0x0050; // 2.3.3.1.11 VtString
	var VT_USTR     = 0x0051; // 2.3.3.1.12 VtUnalignedString
	var VT_CUSTOM   = [VT_STRING, VT_USTR];
}

/* [MS-OSHARED] 2.3.3.2.2.1 Document Summary Information PIDDSI */
var DocSummaryPIDDSI = {
0x01: { n: 'CodePage', t: VT_I2 },
0x02: { n: 'Category', t: VT_STRING },
0x03: { n: 'PresentationFormat', t: VT_STRING },
0x04: { n: 'ByteCount', t: VT_I4 },
0x05: { n: 'LineCount', t: VT_I4 },
0x06: { n: 'ParagraphCount', t: VT_I4 },
0x07: { n: 'SlideCount', t: VT_I4 },
0x08: { n: 'NoteCount', t: VT_I4 },
0x09: { n: 'HiddenCount', t: VT_I4 },
0x0a: { n: 'MultimediaClipCount', t: VT_I4 },
0x0b: { n: 'Scale', t: VT_BOOL },
0x0c: { n: 'HeadingPair', t: VT_VECTOR | VT_VARIANT },
0x0d: { n: 'DocParts', t: VT_VECTOR | VT_LPSTR },
0x0e: { n: 'Manager', t: VT_STRING },
0x0f: { n: 'Company', t: VT_STRING },
0x10: { n: 'LinksDirty', t: VT_BOOL },
0x11: { n: 'CharacterCount', t: VT_I4 },
0x13: { n: 'SharedDoc', t: VT_BOOL },
0x16: { n: 'HLinksChanged', t: VT_BOOL },
0x17: { n: 'AppVersion', t: VT_I4, p: 'version' },
0x1A: { n: 'ContentType', t: VT_STRING },
0x1B: { n: 'ContentStatus', t: VT_STRING },
0x1C: { n: 'Language', t: VT_STRING },
0x1D: { n: 'Version', t: VT_STRING },
0xFF: {}
};

/* [MS-OSHARED] 2.3.3.2.1.1 Summary Information Property Set PIDSI */
var SummaryPIDSI = {
0x01: { n: 'CodePage', t: VT_I2 },
0x02: { n: 'Title', t: VT_STRING },
0x03: { n: 'Subject', t: VT_STRING },
0x04: { n: 'Author', t: VT_STRING },
0x05: { n: 'Keywords', t: VT_STRING },
0x06: { n: 'Comments', t: VT_STRING },
0x07: { n: 'Template', t: VT_STRING },
0x08: { n: 'LastAuthor', t: VT_STRING },
0x09: { n: 'RevNumber', t: VT_STRING },
0x0A: { n: 'EditTime', t: VT_FILETIME },
0x0B: { n: 'LastPrinted', t: VT_FILETIME },
0x0C: { n: 'CreatedDate', t: VT_FILETIME },
0x0D: { n: 'ModifiedDate', t: VT_FILETIME },
0x0E: { n: 'PageCount', t: VT_I4 },
0x0F: { n: 'WordCount', t: VT_I4 },
0x10: { n: 'CharCount', t: VT_I4 },
0x11: { n: 'Thumbnail', t: VT_CF },
0x12: { n: 'ApplicationName', t: VT_LPSTR },
0x13: { n: 'DocumentSecurity', t: VT_I4 },
0xFF: {}
};

/* [MS-OLEPS] 2.18 */
var SpecialProperties = {
0x80000000: { n: 'Locale', t: VT_UI4 },
0x80000003: { n: 'Behavior', t: VT_UI4 },
0x72627262: {}
};

(function() {
	for(var y in SpecialProperties) if(SpecialProperties.hasOwnProperty(y))
	DocSummaryPIDDSI[y] = SummaryPIDSI[y] = SpecialProperties[y];
})();

/* [MS-XLS] 2.4.63 Country/Region codes */
var CountryEnum = {
0x0001: "US", // United States
0x0002: "CA", // Canada
0x0003: "", // Latin America (except Brazil)
0x0007: "RU", // Russia
0x0014: "EG", // Egypt
0x001E: "GR", // Greece
0x001F: "NL", // Netherlands
0x0020: "BE", // Belgium
0x0021: "FR", // France
0x0022: "ES", // Spain
0x0024: "HU", // Hungary
0x0027: "IT", // Italy
0x0029: "CH", // Switzerland
0x002B: "AT", // Austria
0x002C: "GB", // United Kingdom
0x002D: "DK", // Denmark
0x002E: "SE", // Sweden
0x002F: "NO", // Norway
0x0030: "PL", // Poland
0x0031: "DE", // Germany
0x0034: "MX", // Mexico
0x0037: "BR", // Brazil
0x003d: "AU", // Australia
0x0040: "NZ", // New Zealand
0x0042: "TH", // Thailand
0x0051: "JP", // Japan
0x0052: "KR", // Korea
0x0054: "VN", // Viet Nam
0x0056: "CN", // China
0x005A: "TR", // Turkey
0x0069: "JS", // Ramastan
0x00D5: "DZ", // Algeria
0x00D8: "MA", // Morocco
0x00DA: "LY", // Libya
0x015F: "PT", // Portugal
0x0162: "IS", // Iceland
0x0166: "FI", // Finland
0x01A4: "CZ", // Czech Republic
0x0376: "TW", // Taiwan
0x03C1: "LB", // Lebanon
0x03C2: "JO", // Jordan
0x03C3: "SY", // Syria
0x03C4: "IQ", // Iraq
0x03C5: "KW", // Kuwait
0x03C6: "SA", // Saudi Arabia
0x03CB: "AE", // United Arab Emirates
0x03CC: "IL", // Israel
0x03CE: "QA", // Qatar
0x03D5: "IR", // Iran
0xFFFF: "US"  // United States
};

/* [MS-XLS] 2.5.127 */
var XLSFillPattern = [
	null,
	'solid',
	'mediumGray',
	'darkGray',
	'lightGray',
	'darkHorizontal',
	'darkVertical',
	'darkDown',
	'darkUp',
	'darkGrid',
	'darkTrellis',
	'lightHorizontal',
	'lightVertical',
	'lightDown',
	'lightUp',
	'lightGrid',
	'lightTrellis',
	'gray125',
	'gray0625'
];

function rgbify(arr) { return arr.map(function(x) { return [(x>>16)&255,(x>>8)&255,x&255]; }); }

/* [MS-XLS] 2.5.161 */
/* [MS-XLSB] 2.5.75 */
var XLSIcv = rgbify([
	/* Color Constants */
	0x000000,
	0xFFFFFF,
	0xFF0000,
	0x00FF00,
	0x0000FF,
	0xFFFF00,
	0xFF00FF,
	0x00FFFF,

	/* Overridable Defaults */
	0x000000,
	0xFFFFFF,
	0xFF0000,
	0x00FF00,
	0x0000FF,
	0xFFFF00,
	0xFF00FF,
	0x00FFFF,

	0x800000,
	0x008000,
	0x000080,
	0x808000,
	0x800080,
	0x008080,
	0xC0C0C0,
	0x808080,
	0x9999FF,
	0x993366,
	0xFFFFCC,
	0xCCFFFF,
	0x660066,
	0xFF8080,
	0x0066CC,
	0xCCCCFF,

	0x000080,
	0xFF00FF,
	0xFFFF00,
	0x00FFFF,
	0x800080,
	0x800000,
	0x008080,
	0x0000FF,
	0x00CCFF,
	0xCCFFFF,
	0xCCFFCC,
	0xFFFF99,
	0x99CCFF,
	0xFF99CC,
	0xCC99FF,
	0xFFCC99,

	0x3366FF,
	0x33CCCC,
	0x99CC00,
	0xFFCC00,
	0xFF9900,
	0xFF6600,
	0x666699,
	0x969696,
	0x003366,
	0x339966,
	0x003300,
	0x333300,
	0x993300,
	0x993366,
	0x333399,
	0x333333,

	/* Other entries to appease BIFF8/12 */
	0xFFFFFF, /* 0x40 icvForeground ?? */
	0x000000, /* 0x41 icvBackground ?? */
	0x000000, /* 0x42 icvFrame ?? */
	0x000000, /* 0x43 icv3D ?? */
	0x000000, /* 0x44 icv3DText ?? */
	0x000000, /* 0x45 icv3DHilite ?? */
	0x000000, /* 0x46 icv3DShadow ?? */
	0x000000, /* 0x47 icvHilite ?? */
	0x000000, /* 0x48 icvCtlText ?? */
	0x000000, /* 0x49 icvCtlScrl ?? */
	0x000000, /* 0x4A icvCtlInv ?? */
	0x000000, /* 0x4B icvCtlBody ?? */
	0x000000, /* 0x4C icvCtlFrame ?? */
	0x000000, /* 0x4D icvCtlFore ?? */
	0x000000, /* 0x4E icvCtlBack ?? */
	0x000000, /* 0x4F icvCtlNeutral */
	0x000000, /* 0x50 icvInfoBk ?? */
	0x000000 /* 0x51 icvInfoText ?? */
]);

/* Parts enumerated in OPC spec, MS-XLSB and MS-XLSX */
/* 12.3 Part Summary <SpreadsheetML> */
/* 14.2 Part Summary <DrawingML> */
/* [MS-XLSX] 2.1 Part Enumerations */
/* [MS-XLSB] 2.1.7 Part Enumeration */
var ct2type/*{[string]:string}*/ = ({
	/* Workbook */
	"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml": "workbooks",

	/* Worksheet */
	"application/vnd.ms-excel.binIndexWs": "TODO", /* Binary Index */

	/* Macrosheet */
	"application/vnd.ms-excel.intlmacrosheet": "TODO",
	"application/vnd.ms-excel.binIndexMs": "TODO", /* Binary Index */

	/* File Properties */
	"application/vnd.openxmlformats-package.core-properties+xml": "coreprops",
	"application/vnd.openxmlformats-officedocument.custom-properties+xml": "custprops",
	"application/vnd.openxmlformats-officedocument.extended-properties+xml": "extprops",

	/* Custom Data Properties */
	"application/vnd.openxmlformats-officedocument.customXmlProperties+xml": "TODO",
	"application/vnd.openxmlformats-officedocument.spreadsheetml.customProperty": "TODO",

	/* PivotTable */
	"application/vnd.ms-excel.pivotTable": "TODO",
	"application/vnd.openxmlformats-officedocument.spreadsheetml.pivotTable+xml": "TODO",

	/* Chart Colors */
	"application/vnd.ms-office.chartcolorstyle+xml": "TODO",

	/* Chart Style */
	"application/vnd.ms-office.chartstyle+xml": "TODO",

	/* Calculation Chain */
	"application/vnd.ms-excel.calcChain": "calcchains",
	"application/vnd.openxmlformats-officedocument.spreadsheetml.calcChain+xml": "calcchains",

	/* Printer Settings */
	"application/vnd.openxmlformats-officedocument.spreadsheetml.printerSettings": "TODO",

	/* ActiveX */
	"application/vnd.ms-office.activeX": "TODO",
	"application/vnd.ms-office.activeX+xml": "TODO",

	/* Custom Toolbars */
	"application/vnd.ms-excel.attachedToolbars": "TODO",

	/* External Data Connections */
	"application/vnd.ms-excel.connections": "TODO",
	"application/vnd.openxmlformats-officedocument.spreadsheetml.connections+xml": "TODO",

	/* External Links */
	"application/vnd.ms-excel.externalLink": "TODO",
	"application/vnd.openxmlformats-officedocument.spreadsheetml.externalLink+xml": "TODO",

	/* Metadata */
	"application/vnd.ms-excel.sheetMetadata": "TODO",
	"application/vnd.openxmlformats-officedocument.spreadsheetml.sheetMetadata+xml": "TODO",

	/* PivotCache */
	"application/vnd.ms-excel.pivotCacheDefinition": "TODO",
	"application/vnd.ms-excel.pivotCacheRecords": "TODO",
	"application/vnd.openxmlformats-officedocument.spreadsheetml.pivotCacheDefinition+xml": "TODO",
	"application/vnd.openxmlformats-officedocument.spreadsheetml.pivotCacheRecords+xml": "TODO",

	/* Query Table */
	"application/vnd.ms-excel.queryTable": "TODO",
	"application/vnd.openxmlformats-officedocument.spreadsheetml.queryTable+xml": "TODO",

	/* Shared Workbook */
	"application/vnd.ms-excel.userNames": "TODO",
	"application/vnd.ms-excel.revisionHeaders": "TODO",
	"application/vnd.ms-excel.revisionLog": "TODO",
	"application/vnd.openxmlformats-officedocument.spreadsheetml.revisionHeaders+xml": "TODO",
	"application/vnd.openxmlformats-officedocument.spreadsheetml.revisionLog+xml": "TODO",
	"application/vnd.openxmlformats-officedocument.spreadsheetml.userNames+xml": "TODO",

	/* Single Cell Table */
	"application/vnd.ms-excel.tableSingleCells": "TODO",
	"application/vnd.openxmlformats-officedocument.spreadsheetml.tableSingleCells+xml": "TODO",

	/* Slicer */
	"application/vnd.ms-excel.slicer": "TODO",
	"application/vnd.ms-excel.slicerCache": "TODO",
	"application/vnd.ms-excel.slicer+xml": "TODO",
	"application/vnd.ms-excel.slicerCache+xml": "TODO",

	/* Sort Map */
	"application/vnd.ms-excel.wsSortMap": "TODO",

	/* Table */
	"application/vnd.ms-excel.table": "TODO",
	"application/vnd.openxmlformats-officedocument.spreadsheetml.table+xml": "TODO",

	/* Themes */
	"application/vnd.openxmlformats-officedocument.theme+xml": "themes",

	/* Theme Override */
	"application/vnd.openxmlformats-officedocument.themeOverride+xml": "TODO",

	/* Timeline */
	"application/vnd.ms-excel.Timeline+xml": "TODO", /* verify */
	"application/vnd.ms-excel.TimelineCache+xml": "TODO", /* verify */

	/* VBA */
	"application/vnd.ms-office.vbaProject": "vba",
	"application/vnd.ms-office.vbaProjectSignature": "vba",

	/* Volatile Dependencies */
	"application/vnd.ms-office.volatileDependencies": "TODO",
	"application/vnd.openxmlformats-officedocument.spreadsheetml.volatileDependencies+xml": "TODO",

	/* Control Properties */
	"application/vnd.ms-excel.controlproperties+xml": "TODO",

	/* Data Model */
	"application/vnd.openxmlformats-officedocument.model+data": "TODO",

	/* Survey */
	"application/vnd.ms-excel.Survey+xml": "TODO",

	/* Drawing */
	"application/vnd.openxmlformats-officedocument.drawing+xml": "drawings",
	"application/vnd.openxmlformats-officedocument.drawingml.chart+xml": "TODO",
	"application/vnd.openxmlformats-officedocument.drawingml.chartshapes+xml": "TODO",
	"application/vnd.openxmlformats-officedocument.drawingml.diagramColors+xml": "TODO",
	"application/vnd.openxmlformats-officedocument.drawingml.diagramData+xml": "TODO",
	"application/vnd.openxmlformats-officedocument.drawingml.diagramLayout+xml": "TODO",
	"application/vnd.openxmlformats-officedocument.drawingml.diagramStyle+xml": "TODO",

	/* VML */
	"application/vnd.openxmlformats-officedocument.vmlDrawing": "TODO",

	"application/vnd.openxmlformats-package.relationships+xml": "rels",
	"application/vnd.openxmlformats-officedocument.oleObject": "TODO",

	/* Image */
	"image/png": "TODO",

	"sheet": "js"
});

var CT_LIST = (function(){
	var o = {
		workbooks: {
			xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml",
			xlsm: "application/vnd.ms-excel.sheet.macroEnabled.main+xml",
			xlsb: "application/vnd.ms-excel.sheet.binary.macroEnabled.main",
			xltx: "application/vnd.openxmlformats-officedocument.spreadsheetml.template.main+xml"
		},
		strs: { /* Shared Strings */
			xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml",
			xlsb: "application/vnd.ms-excel.sharedStrings"
		},
		comments: { /* Comments */
			xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.comments+xml",
			xlsb: "application/vnd.ms-excel.comments"
		},
		sheets: { /* Worksheet */
			xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml",
			xlsb: "application/vnd.ms-excel.worksheet"
		},
		charts: { /* Chartsheet */
			xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.chartsheet+xml",
			xlsb: "application/vnd.ms-excel.chartsheet"
		},
		dialogs: { /* Dialogsheet */
			xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.dialogsheet+xml",
			xlsb: "application/vnd.ms-excel.dialogsheet"
		},
		macros: { /* Macrosheet (Excel 4.0 Macros) */
			xlsx: "application/vnd.ms-excel.macrosheet+xml",
			xlsb: "application/vnd.ms-excel.macrosheet"
		},
		styles: { /* Styles */
			xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml",
			xlsb: "application/vnd.ms-excel.styles"
		}
	};
	keys(o).forEach(function(k) { if(!o[k].xlsm) o[k].xlsm = o[k].xlsx; });
	keys(o).forEach(function(k){ keys(o[k]).forEach(function(v) { ct2type[o[k][v]] = k; }); });
	return o;
})();

var type2ct/*{[string]:Array<string>}*/ = evert_arr(ct2type);

XMLNS.CT = 'http://schemas.openxmlformats.org/package/2006/content-types';

function parse_ct(data, opts) {
	var ct = ({
		workbooks:[], sheets:[], charts:[], dialogs:[], macros:[],
		rels:[], strs:[], comments:[],
		coreprops:[], extprops:[], custprops:[], themes:[], styles:[],
		calcchains:[], vba: [], drawings: [],
		TODO:[], xmlns: "" });
	if(!data || !data.match) return ct;
	var ctext = {};
	(data.match(tagregex)||[]).forEach(function(x) {
		var y = parsexmltag(x);
		switch(y[0].replace(nsregex,"<")) {
			case '<?xml': break;
			case '<Types': ct.xmlns = y['xmlns' + (y[0].match(/<(\w+):/)||["",""])[1] ]; break;
			case '<Default': ctext[y.Extension] = y.ContentType; break;
			case '<Override':
				if(ct[ct2type[y.ContentType]] !== undefined) ct[ct2type[y.ContentType]].push(y.PartName);
				break;
		}
	});
	if(ct.xmlns !== XMLNS.CT) throw new Error("Unknown Namespace: " + ct.xmlns);
	ct.calcchain = ct.calcchains.length > 0 ? ct.calcchains[0] : "";
	ct.sst = ct.strs.length > 0 ? ct.strs[0] : "";
	ct.style = ct.styles.length > 0 ? ct.styles[0] : "";
	ct.defaults = ctext;
	delete ct.calcchains;
	return ct;
}

var CTYPE_XML_ROOT = writextag('Types', null, {
	'xmlns': XMLNS.CT,
	'xmlns:xsd': XMLNS.xsd,
	'xmlns:xsi': XMLNS.xsi
});

var CTYPE_DEFAULTS = [
	['xml', 'application/xml'],
	['bin', 'application/vnd.ms-excel.sheet.binary.macroEnabled.main'],
	['vml', 'application/vnd.openxmlformats-officedocument.vmlDrawing'],
	/* from test files */
	['bmp', 'image/bmp'],
	['png', 'image/png'],
	['gif', 'image/gif'],
	['emf', 'image/x-emf'],
	['wmf', 'image/x-wmf'],
	['jpg', 'image/jpeg'], ['jpeg', 'image/jpeg'],
	['tif', 'image/tiff'], ['tiff', 'image/tiff'],
	['pdf', 'application/pdf'],
	['rels', type2ct.rels[0]]
].map(function(x) {
	return writextag('Default', null, {'Extension':x[0], 'ContentType': x[1]});
});

function write_ct(ct, opts) {
	var o = [], v;
	o[o.length] = (XML_HEADER);
	o[o.length] = (CTYPE_XML_ROOT);
	o = o.concat(CTYPE_DEFAULTS);
	var f1 = function(w) {
		if(ct[w] && ct[w].length > 0) {
			v = ct[w][0];
			o[o.length] = (writextag('Override', null, {
				'PartName': (v[0] == '/' ? "":"/") + v,
				'ContentType': CT_LIST[w][opts.bookType || 'xlsx']
			}));
		}
	};
	var f2 = function(w) {
		(ct[w]||[]).forEach(function(v) {
			o[o.length] = (writextag('Override', null, {
				'PartName': (v[0] == '/' ? "":"/") + v,
				'ContentType': CT_LIST[w][opts.bookType || 'xlsx']
			}));
		});
	};
	var f3 = function(t) {
		(ct[t]||[]).forEach(function(v) {
			o[o.length] = (writextag('Override', null, {
				'PartName': (v[0] == '/' ? "":"/") + v,
				'ContentType': type2ct[t][0]
			}));
		});
	};
	f1('workbooks');
	f2('sheets');
	f2('charts');
	f3('themes');
	['strs', 'styles'].forEach(f1);
	['coreprops', 'extprops', 'custprops'].forEach(f3);
	f3('vba');
	f3('comments');
	f3('drawings');
	if(o.length>2){ o[o.length] = ('</Types>'); o[1]=o[1].replace("/>",">"); }
	return o.join("");
}
/* 9.3 Relationships */
var RELS = ({
	WB: "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument",
	SHEET: "http://sheetjs.openxmlformats.org/officeDocument/2006/relationships/officeDocument",
	HLINK: "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
	VML: "http://schemas.openxmlformats.org/officeDocument/2006/relationships/vmlDrawing",
	VBA: "http://schemas.microsoft.com/office/2006/relationships/vbaProject"
});

/* 9.3.3 Representing Relationships */
function get_rels_path(file) {
	var n = file.lastIndexOf("/");
	return file.substr(0,n+1) + '_rels/' + file.substr(n+1) + ".rels";
}

function parse_rels(data, currentFilePath) {
	if (!data) return data;
	if (currentFilePath.charAt(0) !== '/') {
		currentFilePath = '/'+currentFilePath;
	}
	var rels = {};
	var hash = {};

	(data.match(tagregex)||[]).forEach(function(x) {
		var y = parsexmltag(x);
		/* 9.3.2.2 OPC_Relationships */
		if (y[0] === '<Relationship') {
			var rel = {}; rel.Type = y.Type; rel.Target = y.Target; rel.Id = y.Id; rel.TargetMode = y.TargetMode;
			var canonictarget = y.TargetMode === 'External' ? y.Target : resolve_path(y.Target, currentFilePath);
			rels[canonictarget] = rel;
			hash[y.Id] = rel;
		}
	});
	rels["!id"] = hash;
	return rels;
}

XMLNS.RELS = 'http://schemas.openxmlformats.org/package/2006/relationships';

var RELS_ROOT = writextag('Relationships', null, {
	//'xmlns:ns0': XMLNS.RELS,
	'xmlns': XMLNS.RELS
});

/* TODO */
function write_rels(rels) {
	var o = [XML_HEADER, RELS_ROOT];
	keys(rels['!id']).forEach(function(rid) {
		o[o.length] = (writextag('Relationship', null, rels['!id'][rid]));
	});
	if(o.length>2){ o[o.length] = ('</Relationships>'); o[1]=o[1].replace("/>",">"); }
	return o.join("");
}

function add_rels(rels, rId, f, type, relobj) {
	if(!relobj) relobj = {};
	if(!rels['!id']) rels['!id'] = {};
	if(rId < 0) for(rId = 1; rels['!id']['rId' + rId]; ++rId){/* empty */}
	relobj.Id = 'rId' + rId;
	relobj.Type = type;
	relobj.Target = f;
	if(relobj.Type == RELS.HLINK) relobj.TargetMode = "External";
	if(rels['!id'][relobj.Id]) throw new Error("Cannot rewrite rId " + rId);
	rels['!id'][relobj.Id] = relobj;
	rels[('/' + relobj.Target).replace("//","/")] = relobj;
	return rId;
}
/* Open Document Format for Office Applications (OpenDocument) Version 1.2 */
/* Part 3 Section 4 Manifest File */
var CT_ODS = "application/vnd.oasis.opendocument.spreadsheet";
function parse_manifest(d, opts) {
	var str = xlml_normalize(d);
	var Rn;
	var FEtag;
	while((Rn = xlmlregex.exec(str))) switch(Rn[3]) {
		case 'manifest': break; // 4.2 <manifest:manifest>
		case 'file-entry': // 4.3 <manifest:file-entry>
			FEtag = parsexmltag(Rn[0], false);
			if(FEtag.path == '/' && FEtag.type !== CT_ODS) throw new Error("This OpenDocument is not a spreadsheet");
			break;
		case 'encryption-data': // 4.4 <manifest:encryption-data>
		case 'algorithm': // 4.5 <manifest:algorithm>
		case 'start-key-generation': // 4.6 <manifest:start-key-generation>
		case 'key-derivation': // 4.7 <manifest:key-derivation>
			throw new Error("Unsupported ODS Encryption");
		default: if(opts && opts.WTF) throw Rn;
	}
}

function write_manifest(manifest, opts) {
	var o = [XML_HEADER];
	o.push('<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.2">\n');
	o.push('  <manifest:file-entry manifest:full-path="/" manifest:version="1.2" manifest:media-type="application/vnd.oasis.opendocument.spreadsheet"/>\n');
	for(var i = 0; i < manifest.length; ++i) o.push('  <manifest:file-entry manifest:full-path="' + manifest[i][0] + '" manifest:media-type="' + manifest[i][1] + '"/>\n');
	o.push('</manifest:manifest>');
	return o.join("");
}

/* Part 3 Section 6 Metadata Manifest File */
function write_rdf_type(file, res, tag) {
	return [
		'  <rdf:Description rdf:about="' + file + '">\n',
		'    <rdf:type rdf:resource="http://docs.oasis-open.org/ns/office/1.2/meta/' + (tag || "odf") + '#' + res + '"/>\n',
		'  </rdf:Description>\n'
	].join("");
}
function write_rdf_has(base, file) {
	return [
		'  <rdf:Description rdf:about="' + base + '">\n',
		'    <ns0:hasPart xmlns:ns0="http://docs.oasis-open.org/ns/office/1.2/meta/pkg#" rdf:resource="' + file + '"/>\n',
		'  </rdf:Description>\n'
	].join("");
}
function write_rdf(rdf, opts) {
	var o = [XML_HEADER];
	o.push('<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n');
	for(var i = 0; i != rdf.length; ++i) {
		o.push(write_rdf_type(rdf[i][0], rdf[i][1]));
		o.push(write_rdf_has("",rdf[i][0]));
	}
	o.push(write_rdf_type("","Document", "pkg"));
	o.push('</rdf:RDF>');
	return o.join("");
}
/* TODO: pull properties */
var write_meta_ods = (function() {
	var payload = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><office:document-meta xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:meta="urn:oasis:names:tc:opendocument:xmlns:meta:1.0" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:xlink="http://www.w3.org/1999/xlink" office:version="1.2"><office:meta><meta:generator>Sheet' + 'JS ' + XLSX.version + '</meta:generator></office:meta></office:document-meta>';
	return function wmo(wb, opts) {
		return payload;
	};
})();

/* ECMA-376 Part II 11.1 Core Properties Part */
/* [MS-OSHARED] 2.3.3.2.[1-2].1 (PIDSI/PIDDSI) */
var CORE_PROPS = [
	["cp:category", "Category"],
	["cp:contentStatus", "ContentStatus"],
	["cp:keywords", "Keywords"],
	["cp:lastModifiedBy", "LastAuthor"],
	["cp:lastPrinted", "LastPrinted"],
	["cp:revision", "RevNumber"],
	["cp:version", "Version"],
	["dc:creator", "Author"],
	["dc:description", "Comments"],
	["dc:identifier", "Identifier"],
	["dc:language", "Language"],
	["dc:subject", "Subject"],
	["dc:title", "Title"],
	["dcterms:created", "CreatedDate", 'date'],
	["dcterms:modified", "ModifiedDate", 'date']
];

XMLNS.CORE_PROPS = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties";
RELS.CORE_PROPS  = 'http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties';

var CORE_PROPS_REGEX = (function() {
	var r = new Array(CORE_PROPS.length);
	for(var i = 0; i < CORE_PROPS.length; ++i) {
		var f = CORE_PROPS[i];
		var g = "(?:"+ f[0].substr(0,f[0].indexOf(":")) +":)"+ f[0].substr(f[0].indexOf(":")+1);
		r[i] = new RegExp("<" + g + "[^>]*>(.*)<\/" + g + ">");
	}
	return r;
})();

function parse_core_props(data) {
	var p = {};

	for(var i = 0; i < CORE_PROPS.length; ++i) {
		var f = CORE_PROPS[i], cur = data.match(CORE_PROPS_REGEX[i]);
		if(cur != null && cur.length > 0) p[f[1]] = cur[1];
		if(f[2] === 'date' && p[f[1]]) p[f[1]] = parseDate(p[f[1]]);
	}

	return p;
}

var CORE_PROPS_XML_ROOT = writextag('cp:coreProperties', null, {
	//'xmlns': XMLNS.CORE_PROPS,
	'xmlns:cp': XMLNS.CORE_PROPS,
	'xmlns:dc': XMLNS.dc,
	'xmlns:dcterms': XMLNS.dcterms,
	'xmlns:dcmitype': XMLNS.dcmitype,
	'xmlns:xsi': XMLNS.xsi
});

function cp_doit(f, g, h, o, p) {
	if(p[f] != null || g == null || g === "") return;
	p[f] = g;
	o[o.length] = (h ? writextag(f,g,h) : writetag(f,g));
}

function write_core_props(cp, _opts) {
	var opts = _opts || {};
	var o = [XML_HEADER, CORE_PROPS_XML_ROOT], p = {};
	if(!cp && !opts.Props) return o.join("");

	if(cp) {
		if(cp.CreatedDate != null) cp_doit("dcterms:created", typeof cp.CreatedDate === "string" ? cp.CreatedDate : write_w3cdtf(cp.CreatedDate, opts.WTF), {"xsi:type":"dcterms:W3CDTF"}, o, p);
		if(cp.ModifiedDate != null) cp_doit("dcterms:modified", typeof cp.ModifiedDate === "string" ? cp.ModifiedDate : write_w3cdtf(cp.ModifiedDate, opts.WTF), {"xsi:type":"dcterms:W3CDTF"}, o, p);
	}

	for(var i = 0; i != CORE_PROPS.length; ++i) {
		var f = CORE_PROPS[i];
		var v = opts.Props && opts.Props[f[1]] != null ? opts.Props[f[1]] : cp ? cp[f[1]] : null;
		if(v === true) v = "1";
		else if(v === false) v = "0";
		else if(typeof v == "number") v = String(v);
		if(v != null) cp_doit(f[0], v, null, o, p);
	}
	if(o.length>2){ o[o.length] = ('</cp:coreProperties>'); o[1]=o[1].replace("/>",">"); }
	return o.join("");
}
/* 15.2.12.3 Extended File Properties Part */
/* [MS-OSHARED] 2.3.3.2.[1-2].1 (PIDSI/PIDDSI) */
var EXT_PROPS = [
	["Application", "Application", "string"],
	["AppVersion", "AppVersion", "string"],
	["Company", "Company", "string"],
	["DocSecurity", "DocSecurity", "string"],
	["Manager", "Manager", "string"],
	["HyperlinksChanged", "HyperlinksChanged", "bool"],
	["SharedDoc", "SharedDoc", "bool"],
	["LinksUpToDate", "LinksUpToDate", "bool"],
	["ScaleCrop", "ScaleCrop", "bool"],
	["HeadingPairs", "HeadingPairs", "raw"],
	["TitlesOfParts", "TitlesOfParts", "raw"]
];

XMLNS.EXT_PROPS = "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties";
RELS.EXT_PROPS  = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties';

function parse_ext_props(data, p) {
	var q = {}; if(!p) p = {};

	EXT_PROPS.forEach(function(f) {
		switch(f[2]) {
			case "string": p[f[1]] = (data.match(matchtag(f[0]))||[])[1]; break;
			case "bool": p[f[1]] = (data.match(matchtag(f[0]))||[])[1] === "true"; break;
			case "raw":
				var cur = data.match(new RegExp("<" + f[0] + "[^>]*>(.*)<\/" + f[0] + ">"));
				if(cur && cur.length > 0) q[f[1]] = cur[1];
				break;
		}
	});

	if(q.HeadingPairs && q.TitlesOfParts) {
		var v = parseVector(q.HeadingPairs);
		var parts = parseVector(q.TitlesOfParts).map(function(x) { return x.v; });
		var idx = 0, len = 0;
		for(var i = 0; i !== v.length; i+=2) {
			len = +(v[i+1].v);
			switch(v[i].v) {
				case "Worksheets":
				case "工作表":
				case "Листы":
				case "ワークシート":
				case "גליונות עבודה":
				case "Arbeitsblätter":
				case "Çalışma Sayfaları":
				case "Feuilles de calcul":
				case "Fogli di lavoro":
				case "Folhas de cálculo":
				case "Planilhas":
				case "Werkbladen":
					p.Worksheets = len;
					p.SheetNames = parts.slice(idx, idx + len);
					break;

				case "Named Ranges":
				case "Benannte Bereiche":
					p.NamedRanges = len;
					p.DefinedNames = parts.slice(idx, idx + len);
					break;

				case "Charts":
				case "Diagramme":
					p.Chartsheets = len;
					p.ChartNames = parts.slice(idx, idx + len);
					break;
			}
			idx += len;
		}
	}

	return p;
}

var EXT_PROPS_XML_ROOT = writextag('Properties', null, {
	'xmlns': XMLNS.EXT_PROPS,
	'xmlns:vt': XMLNS.vt
});

function write_ext_props(cp, opts) {
	var o = [], p = {}, W = writextag;
	if(!cp) cp = {};
	cp.Application = "SheetJS";
	o[o.length] = (XML_HEADER);
	o[o.length] = (EXT_PROPS_XML_ROOT);

	EXT_PROPS.forEach(function(f) {
		if(cp[f[1]] === undefined) return;
		var v;
		switch(f[2]) {
			case 'string': v = String(cp[f[1]]); break;
			case 'bool': v = cp[f[1]] ? 'true' : 'false'; break;
		}
		if(v !== undefined) o[o.length] = (W(f[0], v));
	});

	/* TODO: HeadingPairs, TitlesOfParts */
	o[o.length] = (W('HeadingPairs', W('vt:vector', W('vt:variant', '<vt:lpstr>Worksheets</vt:lpstr>')+W('vt:variant', W('vt:i4', String(cp.Worksheets))), {size:2, baseType:"variant"})));
	o[o.length] = (W('TitlesOfParts', W('vt:vector', cp.SheetNames.map(function(s) { return "<vt:lpstr>" + escapexml(s) + "</vt:lpstr>"; }).join(""), {size: cp.Worksheets, baseType:"lpstr"})));
	if(o.length>2){ o[o.length] = ('</Properties>'); o[1]=o[1].replace("/>",">"); }
	return o.join("");
}
/* 15.2.12.2 Custom File Properties Part */
XMLNS.CUST_PROPS = "http://schemas.openxmlformats.org/officeDocument/2006/custom-properties";
RELS.CUST_PROPS  = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/custom-properties';

var custregex = /<[^>]+>[^<]*/g;
function parse_cust_props(data, opts) {
	var p = {}, name = "";
	var m = data.match(custregex);
	if(m) for(var i = 0; i != m.length; ++i) {
		var x = m[i], y = parsexmltag(x);
		switch(y[0]) {
			case '<?xml': break;
			case '<Properties': break;
			case '<property': name = y.name; break;
			case '</property>': name = null; break;
			default: if (x.indexOf('<vt:') === 0) {
				var toks = x.split('>');
				var type = toks[0].substring(4), text = toks[1];
				/* 22.4.2.32 (CT_Variant). Omit the binary types from 22.4 (Variant Types) */
				switch(type) {
					case 'lpstr': case 'bstr': case 'lpwstr':
						p[name] = unescapexml(text);
						break;
					case 'bool':
						p[name] = parsexmlbool(text, '<vt:bool>');
						break;
					case 'i1': case 'i2': case 'i4': case 'i8': case 'int': case 'uint':
						p[name] = parseInt(text, 10);
						break;
					case 'r4': case 'r8': case 'decimal':
						p[name] = parseFloat(text);
						break;
					case 'filetime': case 'date':
						p[name] = parseDate(text);
						break;
					case 'cy': case 'error':
						p[name] = unescapexml(text);
						break;
					default:
						if(opts.WTF && typeof console !== 'undefined') console.warn('Unexpected', x, type, toks);
				}
			} else if(x.substr(0,2) === "</") {/* empty */
			} else if(opts.WTF) throw new Error(x);
		}
	}
	return p;
}

var CUST_PROPS_XML_ROOT = writextag('Properties', null, {
	'xmlns': XMLNS.CUST_PROPS,
	'xmlns:vt': XMLNS.vt
});

function write_cust_props(cp, opts) {
	var o = [XML_HEADER, CUST_PROPS_XML_ROOT];
	if(!cp) return o.join("");
	var pid = 1;
	keys(cp).forEach(function custprop(k) { ++pid;
		// $FlowIgnore
		o[o.length] = (writextag('property', write_vt(cp[k]), {
			'fmtid': '{D5CDD505-2E9C-101B-9397-08002B2CF9AE}',
			'pid': pid,
			'name': k
		}));
	});
	if(o.length>2){ o[o.length] = '</Properties>'; o[1]=o[1].replace("/>",">"); }
	return o.join("");
}
/* Common Name -> XLML Name */
var XLMLDocPropsMap = {
	Title: 'Title',
	Subject: 'Subject',
	Author: 'Author',
	Keywords: 'Keywords',
	Comments: 'Description',
	LastAuthor: 'LastAuthor',
	RevNumber: 'Revision',
	Application: 'AppName',
	/* TotalTime: 'TotalTime', */
	LastPrinted: 'LastPrinted',
	CreatedDate: 'Created',
	ModifiedDate: 'LastSaved',
	/* Pages */
	/* Words */
	/* Characters */
	Category: 'Category',
	/* PresentationFormat */
	Manager: 'Manager',
	Company: 'Company',
	/* Guid */
	/* HyperlinkBase */
	/* Bytes */
	/* Lines */
	/* Paragraphs */
	/* CharactersWithSpaces */
	AppVersion: 'Version',

	ContentStatus: 'ContentStatus', /* NOTE: missing from schema */
	Identifier: 'Identifier', /* NOTE: missing from schema */
	Language: 'Language' /* NOTE: missing from schema */
};
var evert_XLMLDPM = evert(XLMLDocPropsMap);

function xlml_set_prop(Props, tag, val) {
	tag = evert_XLMLDPM[tag] || tag;
	Props[tag] = val;
}

function xlml_write_docprops(Props, opts) {
	var o = [];
	keys(XLMLDocPropsMap).map(function(m) {
		for(var i = 0; i < CORE_PROPS.length; ++i) if(CORE_PROPS[i][1] == m) return CORE_PROPS[i];
		for(i = 0; i < EXT_PROPS.length; ++i) if(EXT_PROPS[i][1] == m) return EXT_PROPS[i];
		throw m;
	}).forEach(function(p) {
		if(Props[p[1]] == null) return;
		var m = opts && opts.Props && opts.Props[p[1]] != null ? opts.Props[p[1]] : Props[p[1]];
		switch(p[2]) {
			case 'date': m = new Date(m).toISOString().replace(/\.\d*Z/,"Z"); break;
		}
		if(typeof m == 'number') m = String(m);
		else if(m === true || m === false) { m = m ? "1" : "0"; }
		else if(m instanceof Date) m = new Date(m).toISOString().replace(/\.\d*Z/,"");
		o.push(writetag(XLMLDocPropsMap[p[1]] || p[1], m));
	});
	return writextag('DocumentProperties', o.join(""), {xmlns:XLMLNS.o });
}
function xlml_write_custprops(Props, Custprops, opts) {
	var BLACKLIST = ["Worksheets","SheetNames"];
	var T = 'CustomDocumentProperties';
	var o = [];
	if(Props) keys(Props).forEach(function(k) {
if(!Props.hasOwnProperty(k)) return;
		for(var i = 0; i < CORE_PROPS.length; ++i) if(k == CORE_PROPS[i][1]) return;
		for(i = 0; i < EXT_PROPS.length; ++i) if(k == EXT_PROPS[i][1]) return;
		for(i = 0; i < BLACKLIST.length; ++i) if(k == BLACKLIST[i]) return;

		var m = Props[k];
		var t = "string";
		if(typeof m == 'number') { t = "float"; m = String(m); }
		else if(m === true || m === false) { t = "boolean"; m = m ? "1" : "0"; }
		else m = String(m);
		o.push(writextag(escapexmltag(k), m, {"dt:dt":t}));
	});
	if(Custprops) keys(Custprops).forEach(function(k) {
if(!Custprops.hasOwnProperty(k)) return;
		var m = Custprops[k];
		var t = "string";
		if(typeof m == 'number') { t = "float"; m = String(m); }
		else if(m === true || m === false) { t = "boolean"; m = m ? "1" : "0"; }
		else if(m instanceof Date) { t = "dateTime.tz"; m = m.toISOString(); }
		else m = String(m);
		o.push(writextag(escapexmltag(k), m, {"dt:dt":t}));
	});
	return '<' + T + ' xmlns="' + XLMLNS.o + '">' + o.join("") + '</' + T + '>';
}
/* [MS-DTYP] 2.3.3 FILETIME */
/* [MS-OLEDS] 2.1.3 FILETIME (Packet Version) */
/* [MS-OLEPS] 2.8 FILETIME (Packet Version) */
function parse_FILETIME(blob) {
	var dwLowDateTime = blob.read_shift(4), dwHighDateTime = blob.read_shift(4);
	return new Date(((dwHighDateTime/1e7*Math.pow(2,32) + dwLowDateTime/1e7) - 11644473600)*1000).toISOString().replace(/\.000/,"");
}

/* [MS-OSHARED] 2.3.3.1.4 Lpstr */
function parse_lpstr(blob, type, pad) {
	var str = blob.read_shift(0, 'lpstr');
	if(pad) blob.l += (4 - ((str.length+1) & 3)) & 3;
	return str;
}

/* [MS-OSHARED] 2.3.3.1.6 Lpwstr */
function parse_lpwstr(blob, type, pad) {
	var str = blob.read_shift(0, 'lpwstr');
	if(pad) blob.l += (4 - ((str.length+1) & 3)) & 3;
	return str;
}


/* [MS-OSHARED] 2.3.3.1.11 VtString */
/* [MS-OSHARED] 2.3.3.1.12 VtUnalignedString */
function parse_VtStringBase(blob, stringType, pad) {
	if(stringType === 0x1F /*VT_LPWSTR*/) return parse_lpwstr(blob);
	return parse_lpstr(blob, stringType, pad);
}

function parse_VtString(blob, t, pad) { return parse_VtStringBase(blob, t, pad === false ? 0: 4); }
function parse_VtUnalignedString(blob, t) { if(!t) throw new Error("dafuq?"); return parse_VtStringBase(blob, t, 0); }

/* [MS-OSHARED] 2.3.3.1.9 VtVecUnalignedLpstrValue */
function parse_VtVecUnalignedLpstrValue(blob) {
	var length = blob.read_shift(4);
	var ret = [];
	for(var i = 0; i != length; ++i) ret[i] = blob.read_shift(0, 'lpstr');
	return ret;
}

/* [MS-OSHARED] 2.3.3.1.10 VtVecUnalignedLpstr */
function parse_VtVecUnalignedLpstr(blob) {
	return parse_VtVecUnalignedLpstrValue(blob);
}

/* [MS-OSHARED] 2.3.3.1.13 VtHeadingPair */
function parse_VtHeadingPair(blob) {
	var headingString = parse_TypedPropertyValue(blob, VT_USTR);
	var headerParts = parse_TypedPropertyValue(blob, VT_I4);
	return [headingString, headerParts];
}

/* [MS-OSHARED] 2.3.3.1.14 VtVecHeadingPairValue */
function parse_VtVecHeadingPairValue(blob) {
	var cElements = blob.read_shift(4);
	var out = [];
	for(var i = 0; i != cElements / 2; ++i) out.push(parse_VtHeadingPair(blob));
	return out;
}

/* [MS-OSHARED] 2.3.3.1.15 VtVecHeadingPair */
function parse_VtVecHeadingPair(blob) {
	// NOTE: When invoked, wType & padding were already consumed
	return parse_VtVecHeadingPairValue(blob);
}

/* [MS-OLEPS] 2.18.1 Dictionary (uses 2.17, 2.16) */
function parse_dictionary(blob,CodePage) {
	var cnt = blob.read_shift(4);
	var dict = ({});
	for(var j = 0; j != cnt; ++j) {
		var pid = blob.read_shift(4);
		var len = blob.read_shift(4);
		dict[pid] = blob.read_shift(len, (CodePage === 0x4B0 ?'utf16le':'utf8')).replace(chr0,'').replace(chr1,'!');
	}
	if(blob.l & 3) blob.l = (blob.l>>2+1)<<2;
	return dict;
}

/* [MS-OLEPS] 2.9 BLOB */
function parse_BLOB(blob) {
	var size = blob.read_shift(4);
	var bytes = blob.slice(blob.l,blob.l+size);
	if((size & 3) > 0) blob.l += (4 - (size & 3)) & 3;
	return bytes;
}

/* [MS-OLEPS] 2.11 ClipboardData */
function parse_ClipboardData(blob) {
	// TODO
	var o = {};
	o.Size = blob.read_shift(4);
	//o.Format = blob.read_shift(4);
	blob.l += o.Size;
	return o;
}

/* [MS-OLEPS] 2.14 Vector and Array Property Types */
function parse_VtVector(blob, cb) {
	/* [MS-OLEPS] 2.14.2 VectorHeader */
/*	var Length = blob.read_shift(4);
	var o = [];
	for(var i = 0; i != Length; ++i) {
		o.push(cb(blob));
	}
	return o;*/
}

/* [MS-OLEPS] 2.15 TypedPropertyValue */
function parse_TypedPropertyValue(blob, type, _opts) {
	var t = blob.read_shift(2), ret, opts = _opts||{};
	blob.l += 2;
	if(type !== VT_VARIANT)
	if(t !== type && VT_CUSTOM.indexOf(type)===-1) throw new Error('Expected type ' + type + ' saw ' + t);
	switch(type === VT_VARIANT ? t : type) {
		case 0x02 /*VT_I2*/: ret = blob.read_shift(2, 'i'); if(!opts.raw) blob.l += 2; return ret;
		case 0x03 /*VT_I4*/: ret = blob.read_shift(4, 'i'); return ret;
		case 0x0B /*VT_BOOL*/: return blob.read_shift(4) !== 0x0;
		case 0x13 /*VT_UI4*/: ret = blob.read_shift(4); return ret;
		case 0x1E /*VT_LPSTR*/: return parse_lpstr(blob, t, 4).replace(chr0,'');
		case 0x1F /*VT_LPWSTR*/: return parse_lpwstr(blob);
		case 0x40 /*VT_FILETIME*/: return parse_FILETIME(blob);
		case 0x41 /*VT_BLOB*/: return parse_BLOB(blob);
		case 0x47 /*VT_CF*/: return parse_ClipboardData(blob);
		case 0x50 /*VT_STRING*/: return parse_VtString(blob, t, !opts.raw && 4).replace(chr0,'');
		case 0x51 /*VT_USTR*/: return parse_VtUnalignedString(blob, t, 4).replace(chr0,'');
		case 0x100C /*VT_VECTOR|VT_VARIANT*/: return parse_VtVecHeadingPair(blob);
		case 0x101E /*VT_LPSTR*/: return parse_VtVecUnalignedLpstr(blob);
		default: throw new Error("TypedPropertyValue unrecognized type " + type + " " + t);
	}
}
/* [MS-OLEPS] 2.14.2 VectorHeader */
/*function parse_VTVectorVariant(blob) {
	var Length = blob.read_shift(4);

	if(Length & 1 !== 0) throw new Error("VectorHeader Length=" + Length + " must be even");
	var o = [];
	for(var i = 0; i != Length; ++i) {
		o.push(parse_TypedPropertyValue(blob, VT_VARIANT));
	}
	return o;
}*/

/* [MS-OLEPS] 2.20 PropertySet */
function parse_PropertySet(blob, PIDSI) {
	var start_addr = blob.l;
	var size = blob.read_shift(4);
	var NumProps = blob.read_shift(4);
	var Props = [], i = 0;
	var CodePage = 0;
	var Dictionary = -1, DictObj = ({});
	for(i = 0; i != NumProps; ++i) {
		var PropID = blob.read_shift(4);
		var Offset = blob.read_shift(4);
		Props[i] = [PropID, Offset + start_addr];
	}
	var PropH = {};
	for(i = 0; i != NumProps; ++i) {
		if(blob.l !== Props[i][1]) {
			var fail = true;
			if(i>0 && PIDSI) switch(PIDSI[Props[i-1][0]].t) {
				case 0x02 /*VT_I2*/: if(blob.l +2 === Props[i][1]) { blob.l+=2; fail = false; } break;
				case 0x50 /*VT_STRING*/: if(blob.l <= Props[i][1]) { blob.l=Props[i][1]; fail = false; } break;
				case 0x100C /*VT_VECTOR|VT_VARIANT*/: if(blob.l <= Props[i][1]) { blob.l=Props[i][1]; fail = false; } break;
			}
			if(!PIDSI && blob.l <= Props[i][1]) { fail=false; blob.l = Props[i][1]; }
			if(fail) throw new Error("Read Error: Expected address " + Props[i][1] + ' at ' + blob.l + ' :' + i);
		}
		if(PIDSI) {
			var piddsi = PIDSI[Props[i][0]];
			PropH[piddsi.n] = parse_TypedPropertyValue(blob, piddsi.t, {raw:true});
			if(piddsi.p === 'version') PropH[piddsi.n] = String(PropH[piddsi.n] >> 16) + "." + String(PropH[piddsi.n] & 0xFFFF);
			if(piddsi.n == "CodePage") switch(PropH[piddsi.n]) {
				case 0: PropH[piddsi.n] = 1252;
					/* falls through */
				case 874:
				case 932:
				case 936:
				case 949:
				case 950:
				case 1250:
				case 1251:
				case 1253:
				case 1254:
				case 1255:
				case 1256:
				case 1257:
				case 1258:
				case 10000:
				case 1200:
				case 1201:
				case 1252:
				case 65000: case -536:
				case 65001: case -535:
					set_cp(CodePage = PropH[piddsi.n]); break;
				default: throw new Error("Unsupported CodePage: " + PropH[piddsi.n]);
			}
		} else {
			if(Props[i][0] === 0x1) {
				CodePage = PropH.CodePage = parse_TypedPropertyValue(blob, VT_I2);
				set_cp(CodePage);
				if(Dictionary !== -1) {
					var oldpos = blob.l;
					blob.l = Props[Dictionary][1];
					DictObj = parse_dictionary(blob,CodePage);
					blob.l = oldpos;
				}
			} else if(Props[i][0] === 0) {
				if(CodePage === 0) { Dictionary = i; blob.l = Props[i+1][1]; continue; }
				DictObj = parse_dictionary(blob,CodePage);
			} else {
				var name = DictObj[Props[i][0]];
				var val;
				/* [MS-OSHARED] 2.3.3.2.3.1.2 + PROPVARIANT */
				switch(blob[blob.l]) {
					case 0x41 /*VT_BLOB*/: blob.l += 4; val = parse_BLOB(blob); break;
					case 0x1E /*VT_LPSTR*/: blob.l += 4; val = parse_VtString(blob, blob[blob.l-4]); break;
					case 0x1F /*VT_LPWSTR*/: blob.l += 4; val = parse_VtString(blob, blob[blob.l-4]); break;
					case 0x03 /*VT_I4*/: blob.l += 4; val = blob.read_shift(4, 'i'); break;
					case 0x13 /*VT_UI4*/: blob.l += 4; val = blob.read_shift(4); break;
					case 0x05 /*VT_R8*/: blob.l += 4; val = blob.read_shift(8, 'f'); break;
					case 0x0B /*VT_BOOL*/: blob.l += 4; val = parsebool(blob, 4); break;
					case 0x40 /*VT_FILETIME*/: blob.l += 4; val = parseDate(parse_FILETIME(blob)); break;
					default: throw new Error("unparsed value: " + blob[blob.l]);
				}
				PropH[name] = val;
			}
		}
	}
	blob.l = start_addr + size; /* step ahead to skip padding */
	return PropH;
}

/* [MS-OLEPS] 2.21 PropertySetStream */
function parse_PropertySetStream(file, PIDSI) {
	var blob = file.content;
	prep_blob(blob, 0);

	var NumSets, FMTID0, FMTID1, Offset0, Offset1 = 0;
	blob.chk('feff', 'Byte Order: ');

	var vers = blob.read_shift(2); // TODO: check version
	var SystemIdentifier = blob.read_shift(4);
	blob.chk(CFB.utils.consts.HEADER_CLSID, 'CLSID: ');
	NumSets = blob.read_shift(4);
	if(NumSets !== 1 && NumSets !== 2) throw new Error("Unrecognized #Sets: " + NumSets);
	FMTID0 = blob.read_shift(16); Offset0 = blob.read_shift(4);

	if(NumSets === 1 && Offset0 !== blob.l) throw new Error("Length mismatch: " + Offset0 + " !== " + blob.l);
	else if(NumSets === 2) { FMTID1 = blob.read_shift(16); Offset1 = blob.read_shift(4); }
	var PSet0 = parse_PropertySet(blob, PIDSI);

	var rval = ({ SystemIdentifier: SystemIdentifier });
	for(var y in PSet0) rval[y] = PSet0[y];
	//rval.blob = blob;
	rval.FMTID = FMTID0;
	//rval.PSet0 = PSet0;
	if(NumSets === 1) return rval;
	if(blob.l !== Offset1) throw new Error("Length mismatch 2: " + blob.l + " !== " + Offset1);
	var PSet1;
	try { PSet1 = parse_PropertySet(blob, null); } catch(e) {/* empty */}
	for(y in PSet1) rval[y] = PSet1[y];
	rval.FMTID = [FMTID0, FMTID1]; // TODO: verify FMTID0/1
	return rval;
}


function parsenoop2(blob, length) { blob.read_shift(length); return null; }

function parslurp(blob, length, cb) {
	var arr = [], target = blob.l + length;
	while(blob.l < target) arr.push(cb(blob, target - blob.l));
	if(target !== blob.l) throw new Error("Slurp error");
	return arr;
}

function parsebool(blob, length) { return blob.read_shift(length) === 0x1; }

function parseuint16(blob) { return blob.read_shift(2, 'u'); }
function parseuint16a(blob, length) { return parslurp(blob,length,parseuint16);}

/* --- 2.5 Structures --- */

/* [MS-XLS] 2.5.14 Boolean */
var parse_Boolean = parsebool;

/* [MS-XLS] 2.5.10 Bes (boolean or error) */
function parse_Bes(blob) {
	var v = blob.read_shift(1), t = blob.read_shift(1);
	return t === 0x01 ? v : v === 0x01;
}

/* [MS-XLS] 2.5.240 ShortXLUnicodeString */
function parse_ShortXLUnicodeString(blob, length, opts) {
	var cch = blob.read_shift(opts && opts.biff >= 12 ? 2 : 1);
	var width = 1, encoding = 'sbcs-cont';
	var cp = current_codepage;
	if(opts && opts.biff >= 8) current_codepage = 1200;
	if(!opts || opts.biff == 8 ) {
		var fHighByte = blob.read_shift(1);
		if(fHighByte) { width = 2; encoding = 'dbcs-cont'; }
	} else if(opts.biff == 12) {
		width = 2; encoding = 'wstr';
	}
	var o = cch ? blob.read_shift(cch, encoding) : "";
	current_codepage = cp;
	return o;
}

/* 2.5.293 XLUnicodeRichExtendedString */
function parse_XLUnicodeRichExtendedString(blob) {
	var cp = current_codepage;
	current_codepage = 1200;
	var cch = blob.read_shift(2), flags = blob.read_shift(1);
	var fHighByte = flags & 0x1, fExtSt = flags & 0x4, fRichSt = flags & 0x8;
	var width = 1 + (flags & 0x1); // 0x0 -> utf8, 0x1 -> dbcs
	var cRun = 0, cbExtRst;
	var z = {};
	if(fRichSt) cRun = blob.read_shift(2);
	if(fExtSt) cbExtRst = blob.read_shift(4);
	var encoding = (flags & 0x1) ? 'dbcs-cont' : 'sbcs-cont';
	var msg = cch === 0 ? "" : blob.read_shift(cch, encoding);
	if(fRichSt) blob.l += 4 * cRun; //TODO: parse this
	if(fExtSt) blob.l += cbExtRst; //TODO: parse this
	z.t = msg;
	if(!fRichSt) { z.raw = "<t>" + z.t + "</t>"; z.r = z.t; }
	current_codepage = cp;
	return z;
}

/* 2.5.296 XLUnicodeStringNoCch */
function parse_XLUnicodeStringNoCch(blob, cch, opts) {
	var retval;
	if(opts) {
		if(opts.biff >= 2 && opts.biff <= 5) return blob.read_shift(cch, 'sbcs-cont');
		if(opts.biff >= 12) return blob.read_shift(cch, 'dbcs-cont');
	}
	var fHighByte = blob.read_shift(1);
	if(fHighByte===0) { retval = blob.read_shift(cch, 'sbcs-cont'); }
	else { retval = blob.read_shift(cch, 'dbcs-cont'); }
	return retval;
}

/* 2.5.294 XLUnicodeString */
function parse_XLUnicodeString(blob, length, opts) {
	var cch = blob.read_shift(opts && opts.biff == 2 ? 1 : 2);
	if(cch === 0) { blob.l++; return ""; }
	return parse_XLUnicodeStringNoCch(blob, cch, opts);
}
/* BIFF5 override */
function parse_XLUnicodeString2(blob, length, opts) {
	if(opts.biff > 5) return parse_XLUnicodeString(blob, length, opts);
	var cch = blob.read_shift(1);
	if(cch === 0) { blob.l++; return ""; }
	return blob.read_shift(cch, 'sbcs-cont');
}

/* [MS-XLS] 2.5.61 ControlInfo */
var parse_ControlInfo = parsenoop;

/* [MS-OSHARED] 2.3.7.6 URLMoniker TODO: flags */
var parse_URLMoniker = function(blob/*, length, opts*/) {
	var len = blob.read_shift(4), start = blob.l;
	var extra = false;
	if(len > 24) {
		/* look ahead */
		blob.l += len - 24;
		if(blob.read_shift(16) === "795881f43b1d7f48af2c825dc4852763") extra = true;
		blob.l = start;
	}
	var url = blob.read_shift((extra?len-24:len)>>1, 'utf16le').replace(chr0,"");
	if(extra) blob.l += 24;
	return url;
};

/* [MS-OSHARED] 2.3.7.8 FileMoniker TODO: all fields */
var parse_FileMoniker = function(blob, length) {
	var cAnti = blob.read_shift(2);
	var ansiLength = blob.read_shift(4);
	var ansiPath = blob.read_shift(ansiLength, 'cstr');
	var endServer = blob.read_shift(2);
	var versionNumber = blob.read_shift(2);
	var cbUnicodePathSize = blob.read_shift(4);
	if(cbUnicodePathSize === 0) return ansiPath.replace(/\\/g,"/");
	var cbUnicodePathBytes = blob.read_shift(4);
	var usKeyValue = blob.read_shift(2);
	var unicodePath = blob.read_shift(cbUnicodePathBytes>>1, 'utf16le').replace(chr0,"");
	return unicodePath;
};

/* [MS-OSHARED] 2.3.7.2 HyperlinkMoniker TODO: all the monikers */
var parse_HyperlinkMoniker = function(blob, length) {
	var clsid = blob.read_shift(16); length -= 16;
	switch(clsid) {
		case "e0c9ea79f9bace118c8200aa004ba90b": return parse_URLMoniker(blob, length);
		case "0303000000000000c000000000000046": return parse_FileMoniker(blob, length);
		default: throw new Error("Unsupported Moniker " + clsid);
	}
};

/* [MS-OSHARED] 2.3.7.9 HyperlinkString */
var parse_HyperlinkString = function(blob, length) {
	var len = blob.read_shift(4);
	var o = blob.read_shift(len, 'utf16le').replace(chr0, "");
	return o;
};

/* [MS-OSHARED] 2.3.7.1 Hyperlink Object TODO: unify params with XLSX */
var parse_Hyperlink = function(blob, length) {
	var end = blob.l + length;
	var sVer = blob.read_shift(4);
	if(sVer !== 2) throw new Error("Unrecognized streamVersion: " + sVer);
	var flags = blob.read_shift(2);
	blob.l += 2;
	var displayName, targetFrameName, moniker, oleMoniker, location, guid, fileTime;
	if(flags & 0x0010) displayName = parse_HyperlinkString(blob, end - blob.l);
	if(flags & 0x0080) targetFrameName = parse_HyperlinkString(blob, end - blob.l);
	if((flags & 0x0101) === 0x0101) moniker = parse_HyperlinkString(blob, end - blob.l);
	if((flags & 0x0101) === 0x0001) oleMoniker = parse_HyperlinkMoniker(blob, end - blob.l);
	if(flags & 0x0008) location = parse_HyperlinkString(blob, end - blob.l);
	if(flags & 0x0020) guid = blob.read_shift(16);
	if(flags & 0x0040) fileTime = parse_FILETIME(blob, 8);
	blob.l = end;
	var target = (targetFrameName||moniker||oleMoniker);
	if(location) target+="#"+location;
	return {Target: target};
};

/* 2.5.178 LongRGBA */
function parse_LongRGBA(blob, length) { var r = blob.read_shift(1), g = blob.read_shift(1), b = blob.read_shift(1), a = blob.read_shift(1); return [r,g,b,a]; }

/* 2.5.177 LongRGB */
function parse_LongRGB(blob, length) { var x = parse_LongRGBA(blob, length); x[3] = 0; return x; }


/* --- MS-XLS --- */

/* 2.5.19 */
function parse_XLSCell(blob, length) {
	var rw = blob.read_shift(2); // 0-indexed
	var col = blob.read_shift(2);
	var ixfe = blob.read_shift(2);
	return ({r:rw, c:col, ixfe:ixfe});
}

/* 2.5.134 */
function parse_frtHeader(blob) {
	var rt = blob.read_shift(2);
	var flags = blob.read_shift(2); // TODO: parse these flags
	blob.l += 8;
	return {type: rt, flags: flags};
}



function parse_OptXLUnicodeString(blob, length, opts) { return length === 0 ? "" : parse_XLUnicodeString2(blob, length, opts); }

/* 2.5.158 */
//var HIDEOBJENUM = ['SHOWALL', 'SHOWPLACEHOLDER', 'HIDEALL'];
var parse_HideObjEnum = parseuint16;

/* 2.5.344 */
function parse_XTI(blob, length) {
	var iSupBook = blob.read_shift(2), itabFirst = blob.read_shift(2,'i'), itabLast = blob.read_shift(2,'i');
	return [iSupBook, itabFirst, itabLast];
}

/* 2.5.218 */
function parse_RkRec(blob, length) {
	var ixfe = blob.read_shift(2);
	var RK = parse_RkNumber(blob);
	return [ixfe, RK];
}

/* 2.5.1 */
function parse_AddinUdf(blob, length, opts) {
	blob.l += 4; length -= 4;
	var l = blob.l + length;
	var udfName = parse_ShortXLUnicodeString(blob, length, opts);
	var cb = blob.read_shift(2);
	l -= blob.l;
	if(cb !== l) throw new Error("Malformed AddinUdf: padding = " + l + " != " + cb);
	blob.l += cb;
	return udfName;
}

/* 2.5.209 TODO: Check sizes */
function parse_Ref8U(blob, length) {
	var rwFirst = blob.read_shift(2);
	var rwLast = blob.read_shift(2);
	var colFirst = blob.read_shift(2);
	var colLast = blob.read_shift(2);
	return {s:{c:colFirst, r:rwFirst}, e:{c:colLast,r:rwLast}};
}

/* 2.5.211 */
function parse_RefU(blob, length) {
	var rwFirst = blob.read_shift(2);
	var rwLast = blob.read_shift(2);
	var colFirst = blob.read_shift(1);
	var colLast = blob.read_shift(1);
	return {s:{c:colFirst, r:rwFirst}, e:{c:colLast,r:rwLast}};
}

/* 2.5.207 */
var parse_Ref = parse_RefU;

/* 2.5.143 */
function parse_FtCmo(blob, length) {
	blob.l += 4;
	var ot = blob.read_shift(2);
	var id = blob.read_shift(2);
	var flags = blob.read_shift(2);
	blob.l+=12;
	return [id, ot, flags];
}

/* 2.5.149 */
function parse_FtNts(blob, length) {
	var out = {};
	blob.l += 4;
	blob.l += 16; // GUID TODO
	out.fSharedNote = blob.read_shift(2);
	blob.l += 4;
	return out;
}

/* 2.5.142 */
function parse_FtCf(blob, length) {
	var out = {};
	blob.l += 4;
	blob.cf = blob.read_shift(2);
	return out;
}

/* 2.5.140 - 2.5.154 and friends */
function parse_FtSkip(blob, length) { blob.l += 2; blob.l += blob.read_shift(2); }
var FtTab = {
0x00: parse_FtSkip,      /* FtEnd */
0x04: parse_FtSkip,      /* FtMacro */
0x05: parse_FtSkip,      /* FtButton */
0x06: parse_FtSkip,      /* FtGmo */
0x07: parse_FtCf,        /* FtCf */
0x08: parse_FtSkip,      /* FtPioGrbit */
0x09: parse_FtSkip,      /* FtPictFmla */
0x0A: parse_FtSkip,      /* FtCbls */
0x0B: parse_FtSkip,      /* FtRbo */
0x0C: parse_FtSkip,      /* FtSbs */
0x0D: parse_FtNts,       /* FtNts */
0x0E: parse_FtSkip,      /* FtSbsFmla */
0x0F: parse_FtSkip,      /* FtGboData */
0x10: parse_FtSkip,      /* FtEdoData */
0x11: parse_FtSkip,      /* FtRboData */
0x12: parse_FtSkip,      /* FtCblsData */
0x13: parse_FtSkip,      /* FtLbsData */
0x14: parse_FtSkip,      /* FtCblsFmla */
0x15: parse_FtCmo
};
function parse_FtArray(blob, length, ot) {
	var tgt = blob.l + length;
	var fts = [];
	while(blob.l < tgt) {
		var ft = blob.read_shift(2);
		blob.l-=2;
		try {
			fts.push(FtTab[ft](blob, tgt - blob.l));
		} catch(e) { blob.l = tgt; return fts; }
	}
	if(blob.l != tgt) blob.l = tgt; //throw new Error("bad Object Ft-sequence");
	return fts;
}

/* 2.5.129 */
var parse_FontIndex = parseuint16;

/* --- 2.4 Records --- */

/* 2.4.21 */
function parse_BOF(blob, length) {
	var o = {BIFFVer:0, dt:0};
	o.BIFFVer = blob.read_shift(2); length -= 2;
	if(length >= 2) { o.dt = blob.read_shift(2); blob.l -= 2; }
	switch(o.BIFFVer) {
		case 0x0600: /* BIFF8 */
		case 0x0500: /* BIFF5 */
		case 0x0002: case 0x0007: /* BIFF2 */
			break;
		default: if(length > 6) throw new Error("Unexpected BIFF Ver " + o.BIFFVer);
	}

	blob.read_shift(length);
	return o;
}


/* 2.4.146 */
function parse_InterfaceHdr(blob, length) {
	if(length === 0) return 0x04b0;
	var q;
	if((q=blob.read_shift(2))!==0x04b0){/* empty */}
	return 0x04b0;
}


/* 2.4.349 */
function parse_WriteAccess(blob, length, opts) {
	if(opts.enc) { blob.l += length; return ""; }
	var l = blob.l;
	// TODO: make sure XLUnicodeString doesnt overrun
	var UserName = parse_XLUnicodeString(blob, 0, opts);
	blob.read_shift(length + l - blob.l);
	return UserName;
}

/* 2.4.28 */
function parse_BoundSheet8(blob, length, opts) {
	var pos = blob.read_shift(4);
	var hidden = blob.read_shift(1) & 0x03;
	var dt = blob.read_shift(1);
	switch(dt) {
		case 0: dt = 'Worksheet'; break;
		case 1: dt = 'Macrosheet'; break;
		case 2: dt = 'Chartsheet'; break;
		case 6: dt = 'VBAModule'; break;
	}
	var name = parse_ShortXLUnicodeString(blob, 0, opts);
	if(name.length === 0) name = "Sheet1";
	return { pos:pos, hs:hidden, dt:dt, name:name };
}

/* 2.4.265 TODO */
function parse_SST(blob, length) {
	var cnt = blob.read_shift(4);
	var ucnt = blob.read_shift(4);
	var strs = ([]);
	for(var i = 0; i != ucnt; ++i) {
		strs.push(parse_XLUnicodeRichExtendedString(blob));
	}
	strs.Count = cnt; strs.Unique = ucnt;
	return strs;
}

/* 2.4.107 */
function parse_ExtSST(blob, length) {
	var extsst = {};
	extsst.dsst = blob.read_shift(2);
	blob.l += length-2;
	return extsst;
}


/* 2.4.221 TODO: check BIFF2-4 */
function parse_Row(blob, length) {
	var z = ({});
	z.r = blob.read_shift(2);
	z.c = blob.read_shift(2);
	z.cnt = blob.read_shift(2) - z.c;
	var miyRw = blob.read_shift(2);
	blob.l += 4; // reserved(2), unused(2)
	var flags = blob.read_shift(1); // various flags
	blob.l += 3; // reserved(8), ixfe(12), flags(4)
	if(flags & 0x20) z.hidden = true;
	if(flags & 0x40) z.hpt = miyRw / 20;
	return z;
}


/* 2.4.125 */
function parse_ForceFullCalculation(blob, length) {
	var header = parse_frtHeader(blob);
	if(header.type != 0x08A3) throw new Error("Invalid Future Record " + header.type);
	var fullcalc = blob.read_shift(4);
	return fullcalc !== 0x0;
}


var parse_CompressPictures = parsenoop2; /* 2.4.55 Not interesting */



/* 2.4.215 rt */
function parse_RecalcId(blob, length) {
	blob.read_shift(2);
	return blob.read_shift(4);
}

/* 2.4.87 */
function parse_DefaultRowHeight(blob, length, opts) {
	var f = 0;
	if(!(opts && opts.biff == 2)) {
		f = blob.read_shift(2);
	}
	var miyRw = blob.read_shift(2);
	if((opts && opts.biff == 2)) {
		f = 1 - (miyRw >> 15); miyRw &= 0x7fff;
	}
	var fl = {Unsynced:f&1,DyZero:(f&2)>>1,ExAsc:(f&4)>>2,ExDsc:(f&8)>>3};
	return [fl, miyRw];
}

/* 2.4.345 TODO */
function parse_Window1(blob, length) {
	var xWn = blob.read_shift(2), yWn = blob.read_shift(2), dxWn = blob.read_shift(2), dyWn = blob.read_shift(2);
	var flags = blob.read_shift(2), iTabCur = blob.read_shift(2), iTabFirst = blob.read_shift(2);
	var ctabSel = blob.read_shift(2), wTabRatio = blob.read_shift(2);
	return { Pos: [xWn, yWn], Dim: [dxWn, dyWn], Flags: flags, CurTab: iTabCur,
		FirstTab: iTabFirst, Selected: ctabSel, TabRatio: wTabRatio };
}

/* 2.4.122 TODO */
function parse_Font(blob, length, opts) {
	var o = {
		dyHeight: blob.read_shift(2),
		fl: blob.read_shift(2)
	};
	switch(opts && opts.biff || 8) {
		case 2: break;
		case 3: case 4: blob.l += 2; break;
		default: blob.l += 10; break;
	}
	o.name = parse_ShortXLUnicodeString(blob, 0, opts);
	return o;
}

/* 2.4.149 */
function parse_LabelSst(blob, length) {
	var cell = parse_XLSCell(blob);
	cell.isst = blob.read_shift(4);
	return cell;
}

/* 2.4.148 */
function parse_Label(blob, length, opts) {
	var target = blob.l + length;
	var cell = parse_XLSCell(blob, 6);
	if(opts.biff == 2) blob.l++;
	var str = parse_XLUnicodeString(blob, target - blob.l, opts);
	cell.val = str;
	return cell;
}

/* 2.4.126 Number Formats */
function parse_Format(blob, length, opts) {
	var ifmt = blob.read_shift(2);
	var fmtstr = parse_XLUnicodeString2(blob, 0, opts);
	return [ifmt, fmtstr];
}
var parse_BIFF2Format = parse_XLUnicodeString2;

/* 2.4.90 */
function parse_Dimensions(blob, length, opts) {
	var end = blob.l + length;
	var w = opts.biff == 8 || !opts.biff ? 4 : 2;
	var r = blob.read_shift(w), R = blob.read_shift(w);
	var c = blob.read_shift(2), C = blob.read_shift(2);
	blob.l = end;
	return {s: {r:r, c:c}, e: {r:R, c:C}};
}

/* 2.4.220 */
function parse_RK(blob, length) {
	var rw = blob.read_shift(2), col = blob.read_shift(2);
	var rkrec = parse_RkRec(blob);
	return {r:rw, c:col, ixfe:rkrec[0], rknum:rkrec[1]};
}

/* 2.4.175 */
function parse_MulRk(blob, length) {
	var target = blob.l + length - 2;
	var rw = blob.read_shift(2), col = blob.read_shift(2);
	var rkrecs = [];
	while(blob.l < target) rkrecs.push(parse_RkRec(blob));
	if(blob.l !== target) throw new Error("MulRK read error");
	var lastcol = blob.read_shift(2);
	if(rkrecs.length != lastcol - col + 1) throw new Error("MulRK length mismatch");
	return {r:rw, c:col, C:lastcol, rkrec:rkrecs};
}
/* 2.4.174 */
function parse_MulBlank(blob, length) {
	var target = blob.l + length - 2;
	var rw = blob.read_shift(2), col = blob.read_shift(2);
	var ixfes = [];
	while(blob.l < target) ixfes.push(blob.read_shift(2));
	if(blob.l !== target) throw new Error("MulBlank read error");
	var lastcol = blob.read_shift(2);
	if(ixfes.length != lastcol - col + 1) throw new Error("MulBlank length mismatch");
	return {r:rw, c:col, C:lastcol, ixfe:ixfes};
}

/* 2.5.20 2.5.249 TODO: interpret values here */
function parse_CellStyleXF(blob, length, style, opts) {
	var o = {};
	var a = blob.read_shift(4), b = blob.read_shift(4);
	var c = blob.read_shift(4), d = blob.read_shift(2);
	o.patternType = XLSFillPattern[c >> 26];

	if(!opts.cellStyles) return o;
	o.alc = a & 0x07;
	o.fWrap = (a >> 3) & 0x01;
	o.alcV = (a >> 4) & 0x07;
	o.fJustLast = (a >> 7) & 0x01;
	o.trot = (a >> 8) & 0xFF;
	o.cIndent = (a >> 16) & 0x0F;
	o.fShrinkToFit = (a >> 20) & 0x01;
	o.iReadOrder = (a >> 22) & 0x02;
	o.fAtrNum = (a >> 26) & 0x01;
	o.fAtrFnt = (a >> 27) & 0x01;
	o.fAtrAlc = (a >> 28) & 0x01;
	o.fAtrBdr = (a >> 29) & 0x01;
	o.fAtrPat = (a >> 30) & 0x01;
	o.fAtrProt = (a >> 31) & 0x01;

	o.dgLeft = b & 0x0F;
	o.dgRight = (b >> 4) & 0x0F;
	o.dgTop = (b >> 8) & 0x0F;
	o.dgBottom = (b >> 12) & 0x0F;
	o.icvLeft = (b >> 16) & 0x7F;
	o.icvRight = (b >> 23) & 0x7F;
	o.grbitDiag = (b >> 30) & 0x03;

	o.icvTop = c & 0x7F;
	o.icvBottom = (c >> 7) & 0x7F;
	o.icvDiag = (c >> 14) & 0x7F;
	o.dgDiag = (c >> 21) & 0x0F;

	o.icvFore = d & 0x7F;
	o.icvBack = (d >> 7) & 0x7F;
	o.fsxButton = (d >> 14) & 0x01;
	return o;
}
function parse_CellXF(blob, length, opts) {return parse_CellStyleXF(blob,length,0, opts);}
function parse_StyleXF(blob, length, opts) {return parse_CellStyleXF(blob,length,1, opts);}

/* 2.4.353 TODO: actually do this right */
function parse_XF(blob, length, opts) {
	var o = {};
	o.ifnt = blob.read_shift(2); o.ifmt = blob.read_shift(2); o.flags = blob.read_shift(2);
	o.fStyle = (o.flags >> 2) & 0x01;
	length -= 6;
	o.data = parse_CellStyleXF(blob, length, o.fStyle, opts);
	return o;
}

/* 2.4.134 */
function parse_Guts(blob, length) {
	blob.l += 4;
	var out = [blob.read_shift(2), blob.read_shift(2)];
	if(out[0] !== 0) out[0]--;
	if(out[1] !== 0) out[1]--;
	if(out[0] > 7 || out[1] > 7) throw new Error("Bad Gutters: " + out.join("|"));
	return out;
}

/* 2.4.24 */
function parse_BoolErr(blob, length, opts) {
	var cell = parse_XLSCell(blob, 6);
	if(opts.biff == 2) ++blob.l;
	var val = parse_Bes(blob, 2);
	cell.val = val;
	cell.t = (val === true || val === false) ? 'b' : 'e';
	return cell;
}

/* 2.4.180 Number */
function parse_Number(blob, length) {
	var cell = parse_XLSCell(blob, 6);
	var xnum = parse_Xnum(blob, 8);
	cell.val = xnum;
	return cell;
}

var parse_XLHeaderFooter = parse_OptXLUnicodeString; // TODO: parse 2.4.136

/* 2.4.271 */
function parse_SupBook(blob, length, opts) {
	var end = blob.l + length;
	var ctab = blob.read_shift(2);
	var cch = blob.read_shift(2);
	var virtPath;
	if(cch >=0x01 && cch <=0xff) virtPath = parse_XLUnicodeStringNoCch(blob, cch);
	var rgst = blob.read_shift(end - blob.l);
	opts.sbcch = cch;
	return [cch, ctab, virtPath, rgst];
}

/* 2.4.105 TODO */
function parse_ExternName(blob, length, opts) {
	var flags = blob.read_shift(2);
	var body;
	var o = ({
		fBuiltIn: flags & 0x01,
		fWantAdvise: (flags >>> 1) & 0x01,
		fWantPict: (flags >>> 2) & 0x01,
		fOle: (flags >>> 3) & 0x01,
		fOleLink: (flags >>> 4) & 0x01,
		cf: (flags >>> 5) & 0x3FF,
		fIcon: flags >>> 15 & 0x01
	});
	if(opts.sbcch === 0x3A01) body = parse_AddinUdf(blob, length-2, opts);
	//else throw new Error("unsupported SupBook cch: " + opts.sbcch);
	o.body = body || blob.read_shift(length-2);
	if(typeof body === "string") o.Name = body;
	return o;
}

/* 2.4.150 TODO */
function parse_Lbl(blob, length, opts) {
	var target = blob.l + length;
	var flags = blob.read_shift(2);
	var chKey = blob.read_shift(1);
	var cch = blob.read_shift(1);
	var cce = blob.read_shift(opts && opts.biff == 2 ? 1 : 2);
	var itab = 0;
	if(!opts || opts.biff >= 5) {
		blob.l += 2;
		itab = blob.read_shift(2);
		blob.l += 4;
	}
	var name = parse_XLUnicodeStringNoCch(blob, cch, opts);
	var npflen = target - blob.l; if(opts && opts.biff == 2) --npflen;
	var rgce = target == blob.l || cce == 0 ? [] : parse_NameParsedFormula(blob, npflen, opts, cce);
	return {
		chKey: chKey,
		Name: name,
		itab: itab,
		rgce: rgce
	};
}

/* 2.4.106 TODO: verify supbook manipulation */
function parse_ExternSheet(blob, length, opts) {
	if(opts.biff < 8) return parse_ShortXLUnicodeString(blob, length, opts);
	var o = [], target = blob.l + length, len = blob.read_shift(2);
	while(len-- !== 0) o.push(parse_XTI(blob, 6));
		// [iSupBook, itabFirst, itabLast];
	var oo = [];
	return o;
}

/* 2.4.176 TODO: check older biff */
function parse_NameCmt(blob, length, opts) {
	if(opts.biff < 8) { blob.l += length; return; }
	var cchName = blob.read_shift(2);
	var cchComment = blob.read_shift(2);
	var name = parse_XLUnicodeStringNoCch(blob, cchName, opts);
	var comment = parse_XLUnicodeStringNoCch(blob, cchComment, opts);
	return [name, comment];
}

/* 2.4.260 */
function parse_ShrFmla(blob, length, opts) {
	var ref = parse_RefU(blob, 6);
	blob.l++;
	var cUse = blob.read_shift(1);
	length -= 8;
	return [parse_SharedParsedFormula(blob, length, opts), cUse];
}

/* 2.4.4 TODO */
function parse_Array(blob, length, opts) {
	var ref = parse_Ref(blob, 6);
	/* TODO: fAlwaysCalc */
	switch(opts.biff) {
		case 2: blob.l ++; length -= 7; break;
		case 3: case 4: blob.l += 2; length -= 8; break;
		default: blob.l += 6; length -= 12;
	}
	return [ref, parse_ArrayParsedFormula(blob, length, opts, ref)];
}

/* 2.4.173 */
function parse_MTRSettings(blob, length) {
	var fMTREnabled = blob.read_shift(4) !== 0x00;
	var fUserSetThreadCount = blob.read_shift(4) !== 0x00;
	var cUserThreadCount = blob.read_shift(4);
	return [fMTREnabled, fUserSetThreadCount, cUserThreadCount];
}

/* 2.5.186 TODO: BIFF5 */
function parse_NoteSh(blob, length, opts) {
	if(opts.biff < 8) return;
	var row = blob.read_shift(2), col = blob.read_shift(2);
	var flags = blob.read_shift(2), idObj = blob.read_shift(2);
	var stAuthor = parse_XLUnicodeString2(blob, 0, opts);
	if(opts.biff < 8) blob.read_shift(1);
	return [{r:row,c:col}, stAuthor, idObj, flags];
}

/* 2.4.179 */
function parse_Note(blob, length, opts) {
	/* TODO: Support revisions */
	return parse_NoteSh(blob, length, opts);
}

/* 2.4.168 */
function parse_MergeCells(blob, length) {
	var merges = [];
	var cmcs = blob.read_shift(2);
	while (cmcs--) merges.push(parse_Ref8U(blob,length));
	return merges;
}

/* 2.4.181 TODO: parse all the things! */
function parse_Obj(blob, length, opts) {
	if(opts && opts.biff < 8) return parse_BIFF5Obj(blob, length, opts);
	var cmo = parse_FtCmo(blob, 22); // id, ot, flags
	var fts = parse_FtArray(blob, length-22, cmo[1]);
	return { cmo: cmo, ft:fts };
}
/* from older spec */
var parse_BIFF5OT = [];
parse_BIFF5OT[0x08] = function(blob, length, opts) {
	var tgt = blob.l + length;
	blob.l += 10; // todo
	var cf = blob.read_shift(2);
	blob.l += 4;
	var cbPictFmla = blob.read_shift(2);
	blob.l += 2;
	var grbit = blob.read_shift(2);
	blob.l += 4;
	var cchName = blob.read_shift(1);
	blob.l += cchName; // TODO: stName
	blob.l = tgt; // TODO: fmla
	return { fmt:cf };
};

function parse_BIFF5Obj(blob, length, opts) {
	var cnt = blob.read_shift(4);
	var ot = blob.read_shift(2);
	var id = blob.read_shift(2);
	var grbit = blob.read_shift(2);
	var colL = blob.read_shift(2);
	var dxL = blob.read_shift(2);
	var rwT = blob.read_shift(2);
	var dyT = blob.read_shift(2);
	var colR = blob.read_shift(2);
	var dxR = blob.read_shift(2);
	var rwB = blob.read_shift(2);
	var dyB = blob.read_shift(2);
	var cbMacro = blob.read_shift(2);
	blob.l += 6;
	length -= 36;
	var fts = [];
	fts.push((parse_BIFF5OT[ot]||parsenoop)(blob, length, opts));
	return { cmo: [id, ot, grbit], ft:fts };
}

/* 2.4.329 TODO: parse properly */
function parse_TxO(blob, length, opts) {
	var s = blob.l;
	var texts = "";
try {
	blob.l += 4;
	var ot = (opts.lastobj||{cmo:[0,0]}).cmo[1];
	var controlInfo;
	if([0,5,7,11,12,14].indexOf(ot) == -1) blob.l += 6;
	else controlInfo = parse_ControlInfo(blob, 6, opts);
	var cchText = blob.read_shift(2);
	var cbRuns = blob.read_shift(2);
	var ifntEmpty = parse_FontIndex(blob, 2);
	var len = blob.read_shift(2);
	blob.l += len;
	//var fmla = parse_ObjFmla(blob, s + length - blob.l);

	for(var i = 1; i < blob.lens.length-1; ++i) {
		if(blob.l-s != blob.lens[i]) throw new Error("TxO: bad continue record");
		var hdr = blob[blob.l];
		var t = parse_XLUnicodeStringNoCch(blob, blob.lens[i+1]-blob.lens[i]-1);
		texts += t;
		if(texts.length >= (hdr ? cchText : 2*cchText)) break;
	}
	if(texts.length !== cchText && texts.length !== cchText*2) {
		throw new Error("cchText: " + cchText + " != " + texts.length);
	}

	blob.l = s + length;
	/* 2.5.272 TxORuns */
//	var rgTxoRuns = [];
//	for(var j = 0; j != cbRuns/8-1; ++j) blob.l += 8;
//	var cchText2 = blob.read_shift(2);
//	if(cchText2 !== cchText) throw new Error("TxOLastRun mismatch: " + cchText2 + " " + cchText);
//	blob.l += 6;
//	if(s + length != blob.l) throw new Error("TxO " + (s + length) + ", at " + blob.l);
	return { t: texts };
} catch(e) { blob.l = s + length; return { t: texts }; }
}

/* 2.4.140 */
var parse_HLink = function(blob, length) {
	var ref = parse_Ref8U(blob, 8);
	blob.l += 16; /* CLSID */
	var hlink = parse_Hyperlink(blob, length-24);
	return [ref, hlink];
};

/* 2.4.141 */
var parse_HLinkTooltip = function(blob, length) {
	var end = blob.l + length;
	blob.read_shift(2);
	var ref = parse_Ref8U(blob, 8);
	var wzTooltip = blob.read_shift((length-10)/2, 'dbcs-cont');
	wzTooltip = wzTooltip.replace(chr0,"");
	return [ref, wzTooltip];
};

/* 2.4.63 */
function parse_Country(blob, length) {
	var o = [], d;
	d = blob.read_shift(2); o[0] = CountryEnum[d] || d;
	d = blob.read_shift(2); o[1] = CountryEnum[d] || d;
	return o;
}

/* 2.4.50 ClrtClient */
function parse_ClrtClient(blob, length) {
	var ccv = blob.read_shift(2);
	var o = [];
	while(ccv-->0) o.push(parse_LongRGB(blob, 8));
	return o;
}

/* 2.4.188 */
function parse_Palette(blob, length) {
	var ccv = blob.read_shift(2);
	var o = [];
	while(ccv-->0) o.push(parse_LongRGB(blob, 8));
	return o;
}

/* 2.4.354 */
function parse_XFCRC(blob, length) {
	blob.l += 2;
	var o = {cxfs:0, crc:0};
	o.cxfs = blob.read_shift(2);
	o.crc = blob.read_shift(4);
	return o;
}

/* 2.4.53 TODO: parse flags */
/* [MS-XLSB] 2.4.323 TODO: parse flags */
function parse_ColInfo(blob, length, opts) {
	if(!opts.cellStyles) return parsenoop(blob, length);
	var w = opts && opts.biff >= 12 ? 4 : 2;
	var colFirst = blob.read_shift(w);
	var colLast = blob.read_shift(w);
	var coldx = blob.read_shift(w);
	var ixfe = blob.read_shift(w);
	var flags = blob.read_shift(2);
	if(w == 2) blob.l += 2;
	return {s:colFirst, e:colLast, w:coldx, ixfe:ixfe, flags:flags};
}

/* 2.4.257 */
function parse_Setup(blob, length, opts) {
	var o = {};
	blob.l += 16;
	o.header = parse_Xnum(blob, 8);
	o.footer = parse_Xnum(blob, 8);
	blob.l += 2;
	return o;
}

/* 2.4.261 */
function parse_ShtProps(blob, length, opts) {
	var def = {area:false};
	if(opts.biff != 5) { blob.l += length; return def; }
	var d = blob.read_shift(1); blob.l += 3;
	if((d & 0x10)) def.area = true;
	return def;
}

var parse_Style = parsenoop;
var parse_StyleExt = parsenoop;

var parse_Window2 = parsenoop;

var parse_Backup = parsebool; /* 2.4.14 */
var parse_Blank = parse_XLSCell; /* 2.4.20 Just the cell */
var parse_BottomMargin = parse_Xnum; /* 2.4.27 */
var parse_BuiltInFnGroupCount = parseuint16; /* 2.4.30 0x0E or 0x10 but excel 2011 generates 0x11? */
var parse_CalcCount = parseuint16; /* 2.4.31 #Iterations */
var parse_CalcDelta = parse_Xnum; /* 2.4.32 */
var parse_CalcIter = parsebool;  /* 2.4.33 1=iterative calc */
var parse_CalcMode = parseuint16; /* 2.4.34 0=manual, 1=auto (def), 2=table */
var parse_CalcPrecision = parsebool; /* 2.4.35 */
var parse_CalcRefMode = parsenoop2; /* 2.4.36 */
var parse_CalcSaveRecalc = parsebool; /* 2.4.37 */
var parse_CodePage = parseuint16; /* 2.4.52 */
var parse_Compat12 = parsebool; /* 2.4.54 true = no compatibility check */
var parse_Date1904 = parsebool; /* 2.4.77 - 1=1904,0=1900 */
var parse_DefColWidth = parseuint16; /* 2.4.89 */
var parse_DSF = parsenoop2; /* 2.4.94 -- MUST be ignored */
var parse_EntExU2 = parsenoop2; /* 2.4.102 -- Explicitly says to ignore */
var parse_EOF = parsenoop2; /* 2.4.103 */
var parse_Excel9File = parsenoop2; /* 2.4.104 -- Optional and unused */
var parse_FeatHdr = parsenoop2; /* 2.4.112 */
var parse_FontX = parseuint16; /* 2.4.123 */
var parse_Footer = parse_XLHeaderFooter; /* 2.4.124 */
var parse_GridSet = parseuint16; /* 2.4.132, =1 */
var parse_HCenter = parsebool; /* 2.4.135 sheet centered horizontal on print */
var parse_Header = parse_XLHeaderFooter; /* 2.4.136 */
var parse_HideObj = parse_HideObjEnum; /* 2.4.139 */
var parse_InterfaceEnd = parsenoop2; /* 2.4.145 -- noop */
var parse_LeftMargin = parse_Xnum; /* 2.4.151 */
var parse_Mms = parsenoop2; /* 2.4.169 -- Explicitly says to ignore */
var parse_ObjProtect = parsebool; /* 2.4.183 -- must be 1 if present */
var parse_Password = parseuint16; /* 2.4.191 */
var parse_PrintGrid = parsebool; /* 2.4.202 */
var parse_PrintRowCol = parsebool; /* 2.4.203 */
var parse_PrintSize = parseuint16; /* 2.4.204 0:3 */
var parse_Prot4Rev = parsebool; /* 2.4.205 */
var parse_Prot4RevPass = parseuint16; /* 2.4.206 */
var parse_Protect = parsebool; /* 2.4.207 */
var parse_RefreshAll = parsebool; /* 2.4.217 -- must be 0 if not template */
var parse_RightMargin = parse_Xnum; /* 2.4.219 */
var parse_RRTabId = parseuint16a; /* 2.4.241 */
var parse_ScenarioProtect = parsebool; /* 2.4.245 */
var parse_Scl = parseuint16a; /* 2.4.247 num, den */
var parse_String = parse_XLUnicodeString; /* 2.4.268 */
var parse_SxBool = parsebool; /* 2.4.274 */
var parse_TopMargin = parse_Xnum; /* 2.4.328 */
var parse_UsesELFs = parsebool; /* 2.4.337 -- should be 0 */
var parse_VCenter = parsebool; /* 2.4.342 */
var parse_WinProtect = parsebool; /* 2.4.347 */
var parse_WriteProtect = parsenoop; /* 2.4.350 empty record */


/* ---- */
var parse_VerticalPageBreaks = parsenoop;
var parse_HorizontalPageBreaks = parsenoop;
var parse_Selection = parsenoop;
var parse_Continue = parsenoop;
var parse_Pane = parsenoop;
var parse_Pls = parsenoop;
var parse_DCon = parsenoop;
var parse_DConRef = parsenoop;
var parse_DConName = parsenoop;
var parse_XCT = parsenoop;
var parse_CRN = parsenoop;
var parse_FileSharing = parsenoop;
var parse_Uncalced = parsenoop;
var parse_Template = parsenoop;
var parse_Intl = parsenoop;
var parse_WsBool = parsenoop;
var parse_Sort = parsenoop;
var parse_Sync = parsenoop;
var parse_LPr = parsenoop;
var parse_DxGCol = parsenoop;
var parse_FnGroupName = parsenoop;
var parse_FilterMode = parsenoop;
var parse_AutoFilterInfo = parsenoop;
var parse_AutoFilter = parsenoop;
var parse_ScenMan = parsenoop;
var parse_SCENARIO = parsenoop;
var parse_SxView = parsenoop;
var parse_Sxvd = parsenoop;
var parse_SXVI = parsenoop;
var parse_SxIvd = parsenoop;
var parse_SXLI = parsenoop;
var parse_SXPI = parsenoop;
var parse_DocRoute = parsenoop;
var parse_RecipName = parsenoop;
var parse_SXDI = parsenoop;
var parse_SXDB = parsenoop;
var parse_SXFDB = parsenoop;
var parse_SXDBB = parsenoop;
var parse_SXNum = parsenoop;
var parse_SxErr = parsenoop;
var parse_SXInt = parsenoop;
var parse_SXString = parsenoop;
var parse_SXDtr = parsenoop;
var parse_SxNil = parsenoop;
var parse_SXTbl = parsenoop;
var parse_SXTBRGIITM = parsenoop;
var parse_SxTbpg = parsenoop;
var parse_ObProj = parsenoop;
var parse_SXStreamID = parsenoop;
var parse_DBCell = parsenoop;
var parse_SXRng = parsenoop;
var parse_SxIsxoper = parsenoop;
var parse_BookBool = parsenoop;
var parse_DbOrParamQry = parsenoop;
var parse_OleObjectSize = parsenoop;
var parse_SXVS = parsenoop;
var parse_BkHim = parsenoop;
var parse_MsoDrawingGroup = parsenoop;
var parse_MsoDrawing = parsenoop;
var parse_MsoDrawingSelection = parsenoop;
var parse_PhoneticInfo = parsenoop;
var parse_SxRule = parsenoop;
var parse_SXEx = parsenoop;
var parse_SxFilt = parsenoop;
var parse_SxDXF = parsenoop;
var parse_SxItm = parsenoop;
var parse_SxName = parsenoop;
var parse_SxSelect = parsenoop;
var parse_SXPair = parsenoop;
var parse_SxFmla = parsenoop;
var parse_SxFormat = parsenoop;
var parse_SXVDEx = parsenoop;
var parse_SXFormula = parsenoop;
var parse_SXDBEx = parsenoop;
var parse_RRDInsDel = parsenoop;
var parse_RRDHead = parsenoop;
var parse_RRDChgCell = parsenoop;
var parse_RRDRenSheet = parsenoop;
var parse_RRSort = parsenoop;
var parse_RRDMove = parsenoop;
var parse_RRFormat = parsenoop;
var parse_RRAutoFmt = parsenoop;
var parse_RRInsertSh = parsenoop;
var parse_RRDMoveBegin = parsenoop;
var parse_RRDMoveEnd = parsenoop;
var parse_RRDInsDelBegin = parsenoop;
var parse_RRDInsDelEnd = parsenoop;
var parse_RRDConflict = parsenoop;
var parse_RRDDefName = parsenoop;
var parse_RRDRstEtxp = parsenoop;
var parse_LRng = parsenoop;
var parse_CUsr = parsenoop;
var parse_CbUsr = parsenoop;
var parse_UsrInfo = parsenoop;
var parse_UsrExcl = parsenoop;
var parse_FileLock = parsenoop;
var parse_RRDInfo = parsenoop;
var parse_BCUsrs = parsenoop;
var parse_UsrChk = parsenoop;
var parse_UserBView = parsenoop;
var parse_UserSViewBegin = parsenoop; // overloaded
var parse_UserSViewEnd = parsenoop;
var parse_RRDUserView = parsenoop;
var parse_Qsi = parsenoop;
var parse_CondFmt = parsenoop;
var parse_CF = parsenoop;
var parse_DVal = parsenoop;
var parse_DConBin = parsenoop;
var parse_Lel = parsenoop;
var parse_XLSCodeName = parse_XLUnicodeString;
var parse_SXFDBType = parsenoop;
var parse_ObNoMacros = parsenoop;
var parse_Dv = parsenoop;
var parse_Index = parsenoop;
var parse_Table = parsenoop;
var parse_BigName = parsenoop;
var parse_ContinueBigName = parsenoop;
var parse_WebPub = parsenoop;
var parse_QsiSXTag = parsenoop;
var parse_DBQueryExt = parsenoop;
var parse_ExtString = parsenoop;
var parse_TxtQry = parsenoop;
var parse_Qsir = parsenoop;
var parse_Qsif = parsenoop;
var parse_RRDTQSIF = parsenoop;
var parse_OleDbConn = parsenoop;
var parse_WOpt = parsenoop;
var parse_SXViewEx = parsenoop;
var parse_SXTH = parsenoop;
var parse_SXPIEx = parsenoop;
var parse_SXVDTEx = parsenoop;
var parse_SXViewEx9 = parsenoop;
var parse_ContinueFrt = parsenoop;
var parse_RealTimeData = parsenoop;
var parse_ChartFrtInfo = parsenoop;
var parse_FrtWrapper = parsenoop;
var parse_StartBlock = parsenoop;
var parse_EndBlock = parsenoop;
var parse_StartObject = parsenoop;
var parse_EndObject = parsenoop;
var parse_CatLab = parsenoop;
var parse_YMult = parsenoop;
var parse_SXViewLink = parsenoop;
var parse_PivotChartBits = parsenoop;
var parse_FrtFontList = parsenoop;
var parse_SheetExt = parsenoop;
var parse_BookExt = parsenoop;
var parse_SXAddl = parsenoop;
var parse_CrErr = parsenoop;
var parse_HFPicture = parsenoop;
var parse_Feat = parsenoop;
var parse_DataLabExt = parsenoop;
var parse_DataLabExtContents = parsenoop;
var parse_CellWatch = parsenoop;
var parse_FeatHdr11 = parsenoop;
var parse_Feature11 = parsenoop;
var parse_DropDownObjIds = parsenoop;
var parse_ContinueFrt11 = parsenoop;
var parse_DConn = parsenoop;
var parse_List12 = parsenoop;
var parse_Feature12 = parsenoop;
var parse_CondFmt12 = parsenoop;
var parse_CF12 = parsenoop;
var parse_CFEx = parsenoop;
var parse_AutoFilter12 = parsenoop;
var parse_ContinueFrt12 = parsenoop;
var parse_MDTInfo = parsenoop;
var parse_MDXStr = parsenoop;
var parse_MDXTuple = parsenoop;
var parse_MDXSet = parsenoop;
var parse_MDXProp = parsenoop;
var parse_MDXKPI = parsenoop;
var parse_MDB = parsenoop;
var parse_PLV = parsenoop;
var parse_DXF = parsenoop;
var parse_TableStyles = parsenoop;
var parse_TableStyle = parsenoop;
var parse_TableStyleElement = parsenoop;
var parse_NamePublish = parsenoop;
var parse_SortData = parsenoop;
var parse_GUIDTypeLib = parsenoop;
var parse_FnGrp12 = parsenoop;
var parse_NameFnGrp12 = parsenoop;
var parse_HeaderFooter = parsenoop;
var parse_CrtLayout12 = parsenoop;
var parse_CrtMlFrt = parsenoop;
var parse_CrtMlFrtContinue = parsenoop;
var parse_ShapePropsStream = parsenoop;
var parse_TextPropsStream = parsenoop;
var parse_RichTextStream = parsenoop;
var parse_CrtLayout12A = parsenoop;
var parse_Units = parsenoop;
var parse_Chart = parsenoop;
var parse_Series = parsenoop;
var parse_DataFormat = parsenoop;
var parse_LineFormat = parsenoop;
var parse_MarkerFormat = parsenoop;
var parse_AreaFormat = parsenoop;
var parse_PieFormat = parsenoop;
var parse_AttachedLabel = parsenoop;
var parse_SeriesText = parsenoop;
var parse_ChartFormat = parsenoop;
var parse_Legend = parsenoop;
var parse_SeriesList = parsenoop;
var parse_Bar = parsenoop;
var parse_Line = parsenoop;
var parse_Pie = parsenoop;
var parse_Area = parsenoop;
var parse_Scatter = parsenoop;
var parse_CrtLine = parsenoop;
var parse_Axis = parsenoop;
var parse_Tick = parsenoop;
var parse_ValueRange = parsenoop;
var parse_CatSerRange = parsenoop;
var parse_AxisLine = parsenoop;
var parse_CrtLink = parsenoop;
var parse_DefaultText = parsenoop;
var parse_Text = parsenoop;
var parse_ObjectLink = parsenoop;
var parse_Frame = parsenoop;
var parse_Begin = parsenoop;
var parse_End = parsenoop;
var parse_PlotArea = parsenoop;
var parse_Chart3d = parsenoop;
var parse_PicF = parsenoop;
var parse_DropBar = parsenoop;
var parse_Radar = parsenoop;
var parse_Surf = parsenoop;
var parse_RadarArea = parsenoop;
var parse_AxisParent = parsenoop;
var parse_LegendException = parsenoop;
var parse_SerToCrt = parsenoop;
var parse_AxesUsed = parsenoop;
var parse_SBaseRef = parsenoop;
var parse_SerParent = parsenoop;
var parse_SerAuxTrend = parsenoop;
var parse_IFmtRecord = parsenoop;
var parse_Pos = parsenoop;
var parse_AlRuns = parsenoop;
var parse_BRAI = parsenoop;
var parse_SerAuxErrBar = parsenoop;
var parse_SerFmt = parsenoop;
var parse_Chart3DBarShape = parsenoop;
var parse_Fbi = parsenoop;
var parse_BopPop = parsenoop;
var parse_AxcExt = parsenoop;
var parse_Dat = parsenoop;
var parse_PlotGrowth = parsenoop;
var parse_SIIndex = parsenoop;
var parse_GelFrame = parsenoop;
var parse_BopPopCustom = parsenoop;
var parse_Fbi2 = parsenoop;

/* --- Specific to versions before BIFF8 --- */
function parse_ImData(blob, length, opts) {
	var tgt = blob.l + length;
	var cf = blob.read_shift(2);
	var env = blob.read_shift(2);
	var lcb = blob.read_shift(4);
	var o = {fmt:cf, env:env, len:lcb, data:blob.slice(blob.l,blob.l+lcb)};
	blob.l += lcb;
	return o;
}

function parse_BIFF5String(blob) {
	var len = blob.read_shift(1);
	return blob.read_shift(len, 'sbcs-cont');
}

/* BIFF2_??? where ??? is the name from [XLS] */
function parse_BIFF2STR(blob, length, opts) {
	var cell = parse_XLSCell(blob, 6);
	++blob.l;
	var str = parse_XLUnicodeString2(blob, length-7, opts);
	cell.t = 'str';
	cell.val = str;
	return cell;
}

function parse_BIFF2NUM(blob, length, opts) {
	var cell = parse_XLSCell(blob, 6);
	++blob.l;
	var num = parse_Xnum(blob, 8);
	cell.t = 'n';
	cell.val = num;
	return cell;
}

function parse_BIFF2INT(blob, length) {
	var cell = parse_XLSCell(blob, 6);
	++blob.l;
	var num = blob.read_shift(2);
	cell.t = 'n';
	cell.val = num;
	return cell;
}

function parse_BIFF2STRING(blob, length) {
	var cch = blob.read_shift(1);
	if(cch === 0) { blob.l++; return ""; }
	return blob.read_shift(cch, 'sbcs-cont');
}

/* TODO: convert to BIFF8 font struct */
function parse_BIFF2FONTXTRA(blob, length) {
	blob.l += 6; // unknown
	blob.l += 2; // font weight "bls"
	blob.l += 1; // charset
	blob.l += 3; // unknown
	blob.l += 1; // font family
	blob.l += length - 13;
}

/* TODO: parse rich text runs */
function parse_RString(blob, length, opts) {
	var end = blob.l + length;
	var cell = parse_XLSCell(blob, 6);
	var cch = blob.read_shift(2);
	var str = parse_XLUnicodeStringNoCch(blob, cch, opts);
	blob.l = end;
	cell.t = 'str';
	cell.val = str;
	return cell;
}
/* from js-harb (C) 2014-present  SheetJS */
var DBF = (function() {
var dbf_codepage_map = {
	/* Code Pages Supported by Visual FoxPro */
0x01:   437,           0x02:   850,
0x03:  1252,           0x04: 10000,
0x64:   852,           0x65:   866,
0x66:   865,           0x67:   861,
0x68:   895,           0x69:   620,
0x6A:   737,           0x6B:   857,
0x78:   950,           0x79:   949,
0x7A:   936,           0x7B:   932,
0x7C:   874,           0x7D:  1255,
0x7E:  1256,           0x96: 10007,
0x97: 10029,           0x98: 10006,
0xC8:  1250,           0xC9:  1251,
0xCA:  1254,           0xCB:  1253,

	/* shapefile DBF extension */
0x00: 20127,           0x08:   865,
0x09:   437,           0x0A:   850,
0x0B:   437,           0x0D:   437,
0x0E:   850,           0x0F:   437,
0x10:   850,           0x11:   437,
0x12:   850,           0x13:   932,
0x14:   850,           0x15:   437,
0x16:   850,           0x17:   865,
0x18:   437,           0x19:   437,
0x1A:   850,           0x1B:   437,
0x1C:   863,           0x1D:   850,
0x1F:   852,           0x22:   852,
0x23:   852,           0x24:   860,
0x25:   850,           0x26:   866,
0x37:   850,           0x40:   852,
0x4D:   936,           0x4E:   949,
0x4F:   950,           0x50:   874,
0x57:  1252,           0x58:  1252,
0x59:  1252,

0xFF: 16969
};

/* TODO: find an actual specification */
function dbf_to_aoa(buf, opts) {
	var out = [];
	/* TODO: browser based */
	var d = (new_raw_buf(1));
	switch(opts.type) {
		case 'base64': d = s2a(Base64.decode(buf)); break;
		case 'binary': d = s2a(buf); break;
		case 'buffer':
		case 'array': d = buf; break;
	}
	prep_blob(d, 0);
	/* header */
	var ft = d.read_shift(1);
	var memo = false;
	var vfp = false;
	switch(ft) {
		case 0x02: case 0x03: break;
		case 0x30: vfp = true; memo = true; break;
		case 0x31: vfp = true; break;
		case 0x83: memo = true; break;
		case 0x8B: memo = true; break;
		case 0xF5: memo = true; break;
		default: throw new Error("DBF Unsupported Version: " + ft.toString(16));
	}
	var filedate = new Date(), nrow = 0, fpos = 0;
	if(ft == 0x02) nrow = d.read_shift(2);
	filedate = new Date(d.read_shift(1) + 1900, d.read_shift(1) - 1, d.read_shift(1));
	if(ft != 0x02) nrow = d.read_shift(4);
	if(ft != 0x02) fpos = d.read_shift(2);
	var rlen = d.read_shift(2);

	var flags = 0, current_cp = 1252;
	if(ft != 0x02) {
	d.l+=16;
	flags = d.read_shift(1);
	//if(memo && ((flags & 0x02) === 0)) throw new Error("DBF Flags " + flags.toString(16) + " ft " + ft.toString(16));

	/* codepage present in FoxPro */
	if(d[d.l] !== 0) current_cp = dbf_codepage_map[d[d.l]];
	d.l+=1;

	d.l+=2;
	}
	var fields = [], field = {};
	var hend = fpos - 10 - (vfp ? 264 : 0);
	while(ft == 0x02 ? d.l < d.length && d[d.l] != 0x0d: d.l < hend) {
		field = {};
		field.name = cptable.utils.decode(current_cp, d.slice(d.l, d.l+10)).replace(/[\u0000\r\n].*$/g,"");
		d.l += 11;
		field.type = String.fromCharCode(d.read_shift(1));
		if(ft != 0x02) field.offset = d.read_shift(4);
		field.len = d.read_shift(1);
		if(ft == 0x02) field.offset = d.read_shift(2);
		field.dec = d.read_shift(1);
		if(field.name.length) fields.push(field);
		if(ft != 0x02) d.l += 14;
		switch(field.type) {
			// case 'B': break; // Binary
			case 'C': break; // character
			case 'D': break; // date
			case 'F': break; // floating point
			// case 'G': break; // General
			case 'I': break; // long
			case 'L': break; // boolean
			case 'M': break; // memo
			case 'N': break; // number
			// case 'O': break; // double
			// case 'P': break; // Picture
			case 'T': break; // datetime
			case 'Y': break; // currency
			case '0': break; // null ?
			case '+': break; // autoincrement
			case '@': break; // timestamp
			default: throw new Error('Unknown Field Type: ' + field.type);
		}
	}
	if(d[d.l] !== 0x0D) d.l = fpos-1;
	else if(ft == 0x02) d.l = 0x209;
	if(ft != 0x02) {
		if(d.read_shift(1) !== 0x0D) throw new Error("DBF Terminator not found " + d.l + " " + d[d.l]);
		d.l = fpos;
	}
	/* data */
	var R = 0, C = 0;
	out[0] = [];
	for(C = 0; C != fields.length; ++C) out[0][C] = fields[C].name;
	while(nrow-- > 0) {
		if(d[d.l] === 0x2A) { d.l+=rlen; continue; }
		++d.l;
		out[++R] = []; C = 0;
		for(C = 0; C != fields.length; ++C) {
			var dd = d.slice(d.l, d.l+fields[C].len); d.l+=fields[C].len;
			prep_blob(dd, 0);
			var s = cptable.utils.decode(current_cp, dd);
			switch(fields[C].type) {
				case 'C':
					out[R][C] = cptable.utils.decode(current_cp, dd);
					out[R][C] = out[R][C].trim();
					break;
				case 'D':
					if(s.length === 8) out[R][C] = new Date(+s.substr(0,4), +s.substr(4,2)-1, +s.substr(6,2));
					else out[R][C] = s;
					break;
				case 'F': out[R][C] = parseFloat(s.trim()); break;
				case 'I': out[R][C] = dd.read_shift(4, 'i'); break;
				case 'L': switch(s.toUpperCase()) {
					case 'Y': case 'T': out[R][C] = true; break;
					case 'N': case 'F': out[R][C] = false; break;
					case ' ': case '?': out[R][C] = false; break; /* NOTE: technically unitialized */
					default: throw new Error("DBF Unrecognized L:|" + s + "|");
					} break;
				case 'M': /* TODO: handle memo files */
					if(!memo) throw new Error("DBF Unexpected MEMO for type " + ft.toString(16));
					out[R][C] = "##MEMO##" + dd.read_shift(4);
					break;
				case 'N': out[R][C] = +s.replace(/\u0000/g,"").trim(); break;
				case 'T':
					var day = dd.read_shift(4), ms = dd.read_shift(4);
					throw new Error(day + " | " + ms);
					//out[R][C] = new Date(); // TODO
					//break;
				case 'Y': out[R][C] = dd.read(4,'i')/1e4; break;
				case '0':
					if(fields[C].name === '_NullFlags') break;
					/* falls through */
				default: throw new Error("DBF Unsupported data type " + fields[C].type);
			}
		}
	}
	if(ft != 0x02) if(d.l < d.length && d[d.l++] != 0x1A) throw new Error("DBF EOF Marker missing " + (d.l-1) + " of " + d.length + " " + d[d.l-1].toString(16));
	return out;
}

function dbf_to_sheet(buf, opts) {
	var o = opts || {};
	if(!o.dateNF) o.dateNF = "yyyymmdd";
	return aoa_to_sheet(dbf_to_aoa(buf, o), o);
}

function dbf_to_workbook(buf, opts) {
	try { return sheet_to_workbook(dbf_to_sheet(buf, opts), opts); }
	catch(e) { if(opts && opts.WTF) throw e; }
	return ({SheetNames:[],Sheets:{}});
}
	return {
		to_workbook: dbf_to_workbook,
		to_sheet: dbf_to_sheet
	};
})();

var SYLK = (function() {
	/* TODO: find an actual specification */
	function sylk_to_aoa(d, opts) {
		switch(opts.type) {
			case 'base64': return sylk_to_aoa_str(Base64.decode(d), opts);
			case 'binary': return sylk_to_aoa_str(d, opts);
			case 'buffer': return sylk_to_aoa_str(d.toString('binary'), opts);
			case 'array': return sylk_to_aoa_str(cc2str(d), opts);
		}
		throw new Error("Unrecognized type " + opts.type);
	}
	function sylk_to_aoa_str(str, opts) {
		var records = str.split(/[\n\r]+/), R = -1, C = -1, ri = 0, rj = 0, arr = [];
		var formats = [];
		var next_cell_format = null;
		var sht = {}, rowinfo = [], colinfo = [], cw = [];
		var Mval = 0, j;
		for (; ri !== records.length; ++ri) {
			Mval = 0;
			var rstr=records[ri].trim();
			var record=rstr.replace(/;;/g, "\u0001").split(";").map(function(x) { return x.replace(/\u0001/g, ";"); });
			var RT=record[0], val;
			if(rstr.length > 0) switch(RT) {
			case 'ID': break; /* header */
			case 'E': break; /* EOF */
			case 'B': break; /* dimensions */
			case 'O': break; /* options? */
			case 'P':
				if(record[1].charAt(0) == 'P')
					formats.push(rstr.substr(3).replace(/;;/g, ";"));
				break;
			case 'C':
			for(rj=1; rj<record.length; ++rj) switch(record[rj].charAt(0)) {
				case 'X': C = parseInt(record[rj].substr(1))-1; break;
				case 'Y':
					R = parseInt(record[rj].substr(1))-1; C = 0;
					for(j = arr.length; j <= R; ++j) arr[j] = [];
					break;
				case 'K':
					val = record[rj].substr(1);
					if(val.charAt(0) === '"') val = val.substr(1,val.length - 2);
					else if(val === 'TRUE') val = true;
					else if(val === 'FALSE') val = false;
					else if(+val === +val) {
						val = +val;
						if(next_cell_format !== null && SSF.is_date(next_cell_format)) val = numdate(val);
					} else if(!isNaN(fuzzydate(val).getDate())) {
						val = parseDate(val);
					}
					arr[R][C] = val;
					next_cell_format = null;
					break;
				case 'E':
					var formula = rc_to_a1(record[rj].substr(1), {r:R,c:C});
					arr[R][C] = [arr[R][C], formula];
					break;
				default: if(opts && opts.WTF) throw new Error("SYLK bad record " + rstr);
			} break;
			case 'F':
			var F_seen = 0;
			for(rj=1; rj<record.length; ++rj) switch(record[rj].charAt(0)) {
				case 'X': C = parseInt(record[rj].substr(1))-1; ++F_seen; break;
				case 'Y':
					R = parseInt(record[rj].substr(1))-1; /*C = 0;*/
					for(j = arr.length; j <= R; ++j) arr[j] = [];
					break;
				case 'M': Mval = parseInt(record[rj].substr(1)) / 20; break;
				case 'F': break; /* ??? */
				case 'P':
					next_cell_format = formats[parseInt(record[rj].substr(1))];
					break;
				case 'S': break; /* cell style */
				case 'D': break; /* column */
				case 'N': break; /* font */
				case 'W':
					cw = record[rj].substr(1).split(" ");
					for(j = parseInt(cw[0], 10); j <= parseInt(cw[1], 10); ++j) {
						Mval = parseInt(cw[2], 10);
						colinfo[j-1] = Mval == 0 ? {hidden:true}: {wch:Mval}; process_col(colinfo[j-1]);
					} break;
				case 'C': /* default column format */
					C = parseInt(record[rj].substr(1))-1;
					if(!colinfo[C]) colinfo[C] = {};
					break;
				case 'R': /* row properties */
					R = parseInt(record[rj].substr(1))-1;
					if(!rowinfo[R]) rowinfo[R] = {};
					if(Mval > 0) { rowinfo[R].hpt = Mval; rowinfo[R].hpx = pt2px(Mval); }
					else if(Mval == 0) rowinfo[R].hidden = true;
					break;
				default: if(opts && opts.WTF) throw new Error("SYLK bad record " + rstr);
			}
			if(F_seen < 1) next_cell_format = null; break;
			default: if(opts && opts.WTF) throw new Error("SYLK bad record " + rstr);
			}
		}
		if(rowinfo.length > 0) sht['!rows'] = rowinfo;
		if(colinfo.length > 0) sht['!cols'] = colinfo;
		return [arr, sht];
	}

	function sylk_to_sheet(str, opts) {
		var aoasht = sylk_to_aoa(str, opts);
		var aoa = aoasht[0], ws = aoasht[1];
		var o = aoa_to_sheet(aoa, opts);
		keys(ws).forEach(function(k) { o[k] = ws[k]; });
		return o;
	}

	function sylk_to_workbook(str, opts) { return sheet_to_workbook(sylk_to_sheet(str, opts), opts); }

	function write_ws_cell_sylk(cell, ws, R, C, opts) {
		var o = "C;Y" + (R+1) + ";X" + (C+1) + ";K";
		switch(cell.t) {
			case 'n':
				o += (cell.v||0);
				if(cell.f && !cell.F) o += ";E" + a1_to_rc(cell.f, {r:R, c:C}); break;
			case 'b': o += cell.v ? "TRUE" : "FALSE"; break;
			case 'e': o += cell.w || cell.v; break;
			case 'd': o += '"' + (cell.w || cell.v) + '"'; break;
			case 's': o += '"' + cell.v.replace(/"/g,"") + '"'; break;
		}
		return o;
	}

	function write_ws_cols_sylk(out, cols) {
		cols.forEach(function(col, i) {
			var rec = "F;W" + (i+1) + " " + (i+1) + " ";
			if(col.hidden) rec += "0";
			else {
				if(typeof col.width == 'number') col.wpx = width2px(col.width);
				if(typeof col.wpx == 'number') col.wch = px2char(col.wpx);
				if(typeof col.wch == 'number') rec += Math.round(col.wch);
			}
			if(rec.charAt(rec.length - 1) != " ") out.push(rec);
		});
	}

	function write_ws_rows_sylk(out, rows) {
		rows.forEach(function(row, i) {
			var rec = "F;";
			if(row.hidden) rec += "M0;";
			else if(row.hpt) rec += "M" + 20 * row.hpt + ";";
			else if(row.hpx) rec += "M" + 20 * px2pt(row.hpx) + ";";
			if(rec.length > 2) out.push(rec + "R" + (i+1));
		});
	}

	function sheet_to_sylk(ws, opts) {
		var preamble = ["ID;PWXL;N;E"], o = [];
		var r = decode_range(ws['!ref']), cell;
		var dense = Array.isArray(ws);
		var RS = "\r\n";

		preamble.push("P;PGeneral");
		preamble.push("F;P0;DG0G8;M255");
		if(ws['!cols']) write_ws_cols_sylk(preamble, ws['!cols']);
		if(ws['!rows']) write_ws_rows_sylk(preamble, ws['!rows']);

		preamble.push("B;Y" + (r.e.r - r.s.r + 1) + ";X" + (r.e.c - r.s.c + 1) + ";D" + [r.s.c,r.s.r,r.e.c,r.e.r].join(" "));
		for(var R = r.s.r; R <= r.e.r; ++R) {
			for(var C = r.s.c; C <= r.e.c; ++C) {
				var coord = encode_cell({r:R,c:C});
				cell = dense ? (ws[R]||[])[C]: ws[coord];
				if(!cell || cell.v == null && (!cell.f || cell.F)) continue;
				o.push(write_ws_cell_sylk(cell, ws, R, C, opts));
			}
		}
		return preamble.join(RS) + RS + o.join(RS) + RS + "E" + RS;
	}

	return {
		to_workbook: sylk_to_workbook,
		to_sheet: sylk_to_sheet,
		from_sheet: sheet_to_sylk
	};
})();

var DIF = (function() {
	function dif_to_aoa(d, opts) {
		switch(opts.type) {
			case 'base64': return dif_to_aoa_str(Base64.decode(d), opts);
			case 'binary': return dif_to_aoa_str(d, opts);
			case 'buffer': return dif_to_aoa_str(d.toString('binary'), opts);
			case 'array': return dif_to_aoa_str(cc2str(d), opts);
		}
		throw new Error("Unrecognized type " + opts.type);
	}
	function dif_to_aoa_str(str, opts) {
		var records = str.split('\n'), R = -1, C = -1, ri = 0, arr = [];
		for (; ri !== records.length; ++ri) {
			if (records[ri].trim() === 'BOT') { arr[++R] = []; C = 0; continue; }
			if (R < 0) continue;
			var metadata = records[ri].trim().split(",");
			var type = metadata[0], value = metadata[1];
			++ri;
			var data = records[ri].trim();
			switch (+type) {
				case -1:
					if (data === 'BOT') { arr[++R] = []; C = 0; continue; }
					else if (data !== 'EOD') throw new Error("Unrecognized DIF special command " + data);
					break;
				case 0:
					if(data === 'TRUE') arr[R][C] = true;
					else if(data === 'FALSE') arr[R][C] = false;
					else if(+value == +value) arr[R][C] = +value;
					else if(!isNaN(fuzzydate(value).getDate())) arr[R][C] = parseDate(value);
					else arr[R][C] = value;
					++C; break;
				case 1:
					data = data.substr(1,data.length-2);
					arr[R][C++] = data !== '' ? data : null;
					break;
			}
			if (data === 'EOD') break;
		}
		return arr;
	}

	function dif_to_sheet(str, opts) { return aoa_to_sheet(dif_to_aoa(str, opts), opts); }
	function dif_to_workbook(str, opts) { return sheet_to_workbook(dif_to_sheet(str, opts), opts); }

	var sheet_to_dif = (function() {
		var push_field = function pf(o, topic, v, n, s) {
			o.push(topic);
			o.push(v + "," + n);
			o.push('"' + s.replace(/"/g,'""') + '"');
		};
		var push_value = function po(o, type, v, s) {
			o.push(type + "," + v);
			o.push(type == 1 ? '"' + s.replace(/"/g,'""') + '"' : s);
		};
		return function sheet_to_dif(ws, opts) {
			var o = [];
			var r = decode_range(ws['!ref']), cell;
			var dense = Array.isArray(ws);
			push_field(o, "TABLE", 0, 1, "sheetjs");
			push_field(o, "VECTORS", 0, r.e.r - r.s.r + 1,"");
			push_field(o, "TUPLES", 0, r.e.c - r.s.c + 1,"");
			push_field(o, "DATA", 0, 0,"");
			for(var R = r.s.r; R <= r.e.r; ++R) {
				push_value(o, -1, 0, "BOT");
				for(var C = r.s.c; C <= r.e.c; ++C) {
					var coord = encode_cell({r:R,c:C});
					cell = dense ? (ws[R]||[])[C] : ws[coord];
					if(!cell) { push_value(o, 1, 0, ""); continue;}
					switch(cell.t) {
						case 'n':
							var val = DIF_XL ? cell.w : cell.v;
							if(!val && cell.v != null) val = cell.v;
							if(val == null) {
								if(DIF_XL && cell.f && !cell.F) push_value(o, 1, 0, "=" + cell.f);
								else push_value(o, 1, 0, "");
							}
							else push_value(o, 0, val, "V");
							break;
						case 'b':
							push_value(o, 0, cell.v ? 1 : 0, cell.v ? "TRUE" : "FALSE");
							break;
						case 's':
							push_value(o, 1, 0, (!DIF_XL || isNaN(cell.v)) ? cell.v : '="' + cell.v + '"');
							break;
						case 'd':
							if(!cell.w) cell.w = SSF.format(cell.z || SSF._table[14], datenum(parseDate(cell.v)));
							if(DIF_XL) push_value(o, 0, cell.w, "V");
							else push_value(o, 1, 0, cell.w);
							break;
						default: push_value(o, 1, 0, "");
					}
				}
			}
			push_value(o, -1, 0, "EOD");
			var RS = "\r\n";
			var oo = o.join(RS);
			//while((oo.length & 0x7F) != 0) oo += "\0";
			return oo;
		};
	})();
	return {
		to_workbook: dif_to_workbook,
		to_sheet: dif_to_sheet,
		from_sheet: sheet_to_dif
	};
})();

var PRN = (function() {
	function set_text_arr(data, arr, R, C) {
		if(data === 'TRUE') arr[R][C] = true;
		else if(data === 'FALSE') arr[R][C] = false;
		else if(data === ""){/* empty */}
		else if(+data == +data) arr[R][C] = +data;
		else if(!isNaN(fuzzydate(data).getDate())) arr[R][C] = parseDate(data);
		else arr[R][C] = data;
	}

	function prn_to_aoa_str(f, opts) {
		var arr = ([]);
		if(!f || f.length === 0) return arr;
		var lines = f.split(/[\r\n]/);
		var L = lines.length - 1;
		while(L >= 0 && lines[L].length === 0) --L;
		var start = 10, idx = 0;
		var R = 0;
		for(; R <= L; ++R) {
			idx = lines[R].indexOf(" ");
			if(idx == -1) idx = lines[R].length; else idx++;
			start = Math.max(start, idx);
		}
		for(R = 0; R <= L; ++R) {
			arr[R] = [];
			/* TODO: confirm that widths are always 10 */
			var C = 0;
			set_text_arr(lines[R].slice(0, start).trim(), arr, R, C);
			for(C = 1; C <= (lines[R].length - start)/10 + 1; ++C)
				set_text_arr(lines[R].slice(start+(C-1)*10,start+C*10).trim(),arr,R,C);
		}
		return arr;
	}

	function dsv_to_sheet_str(str, opts) {
		var o = opts || {};
		var sep = "";
		if(DENSE != null && o.dense == null) o.dense = DENSE;
		var ws = o.dense ? ([]) : ({});
		var range = ({s: {c:0, r:0}, e: {c:0, r:0}});

		/* known sep */
		if(str.substr(0,4) == "sep=" && str.charCodeAt(5) == 10) { sep = str.charAt(4); str = str.substr(6); }
		else if(str.substr(0,1024).indexOf("\t") == -1) sep = ","; else sep = "\t";
		var R = 0, C = 0, v = 0;
		var start = 0, end = 0, sepcc = sep.charCodeAt(0), instr = false, cc=0;
		str = str.replace(/\r\n/mg, "\n");
		function finish_cell() {
			var s = str.slice(start, end);
			var cell = ({});
			if(s.charCodeAt(0) == 0x3D) { cell.t = 'n'; cell.f = s.substr(1); }
			else if(s == "TRUE") { cell.t = 'b'; cell.v = true; }
			else if(s == "FALSE") { cell.t = 'b'; cell.v = false; }
			else if(!isNaN(v = +s)) { cell.t = 'n'; cell.w = s; cell.v = v; }
			else if(!isNaN(fuzzydate(s).getDate())) {
				cell.z = o.dateNF || SSF._table[14];
				if(o.cellDates) { cell.t = 'd'; cell.v = parseDate(s); }
				else { cell.t = 'n'; cell.v = datenum(parseDate(s)); }
				cell.w = SSF.format(cell.z, cell.v instanceof Date ? datenum(cell.v):cell.v);
			} else {
				cell.t = 's';
				if(s.charAt(0) == '"' && s.charAt(s.length - 1) == '"') s = s.slice(1,-1).replace(/""/g,'"');
				cell.v = s;
			}
			if(o.dense) { if(!ws[R]) ws[R] = []; ws[R][C] = cell; }
			else ws[encode_cell({c:C,r:R})] = cell;
			start = end+1;
			if(range.e.c < C) range.e.c = C;
			if(range.e.r < R) range.e.r = R;
			if(cc == sepcc) ++C; else { C = 0; ++R; }
		}
		for(;end < str.length;++end) switch((cc=str.charCodeAt(end))) {
			case 0x22: instr = !instr; break;
			case sepcc: case 0x0a: case 0x0d: if(!instr) finish_cell(); break;
			default: break;
		}
		if(end - start > 0) finish_cell();

		ws['!ref'] = encode_range(range);
		return ws;
	}

	function prn_to_sheet_str(str, opts) {
		if(str.substr(0,4) == "sep=") return dsv_to_sheet_str(str, opts);
		if(str.indexOf("\t") >= 0 || str.indexOf(",") >= 0) return dsv_to_sheet_str(str, opts);
		return aoa_to_sheet(prn_to_aoa_str(str, opts), opts);
	}

	function prn_to_sheet(d, opts) {
		var str = "", bytes = firstbyte(d, opts);
		switch(opts.type) {
			case 'base64': str = Base64.decode(d); break;
			case 'binary': str = d; break;
			case 'buffer': str = d.toString('binary'); break;
			case 'array': str = cc2str(d); break;
			default: throw new Error("Unrecognized type " + opts.type);
		}
		if(bytes[0] == 0xEF && bytes[1] == 0xBB && bytes[2] == 0xBF) str = utf8read(str);
		return prn_to_sheet_str(str, opts);
	}

	function prn_to_workbook(str, opts) { return sheet_to_workbook(prn_to_sheet(str, opts), opts); }

	function sheet_to_prn(ws, opts) {
		var o = [];
		var r = decode_range(ws['!ref']), cell;
		var dense = Array.isArray(ws);
		for(var R = r.s.r; R <= r.e.r; ++R) {
			var oo = [];
			for(var C = r.s.c; C <= r.e.c; ++C) {
				var coord = encode_cell({r:R,c:C});
				cell = dense ? (ws[R]||[])[C] : ws[coord];
				if(!cell || cell.v == null) { oo.push("          "); continue; }
				var w = (cell.w || (format_cell(cell), cell.w) || "").substr(0,10);
				while(w.length < 10) w += " ";
				oo.push(w + (C == 0 ? " " : ""));
			}
			o.push(oo.join(""));
		}
		return o.join("\n");
	}

	return {
		to_workbook: prn_to_workbook,
		to_sheet: prn_to_sheet,
		from_sheet: sheet_to_prn
	};
})();

/* Excel defaults to SYLK but warns if data is not valid */
function read_wb_ID(d, opts) {
	var o = opts || {}, OLD_WTF = !!o.WTF; o.WTF = true;
	try {
		var out = SYLK.to_workbook(d, o);
		o.WTF = OLD_WTF;
		return out;
	} catch(e) {
		o.WTF = OLD_WTF;
		if(!e.message.match(/SYLK bad record ID/) && OLD_WTF) throw e;
		return PRN.to_workbook(d, opts);
	}
}

var WK_ = (function() {
	function lotushopper(data, cb, opts) {
		if(!data) return;
		prep_blob(data, data.l || 0);
		var Enum = opts.Enum || WK1Enum;
		while(data.l < data.length) {
			var RT = data.read_shift(2);
			var R = Enum[RT] || Enum[0xFF];
			var length = data.read_shift(2);
			var tgt = data.l + length;
			var d = R.f(data, length, opts);
			data.l = tgt;
			if(cb(d, R.n, RT)) return;
		}
	}

	function lotus_to_workbook(d, opts) {
		switch(opts.type) {
			case 'base64': return lotus_to_workbook_buf(s2a(Base64.decode(d)), opts);
			case 'binary': return lotus_to_workbook_buf(s2a(d), opts);
			case 'buffer':
			case 'array': return lotus_to_workbook_buf(d, opts);
		}
		throw "Unsupported type " + opts.type;
	}

	function lotus_to_workbook_buf(d,opts) {
		if(!d) return d;
		var o = opts || {};
		if(DENSE != null && o.dense == null) o.dense = DENSE;
		var s = ((o.dense ? [] : {})), n = "Sheet1", sidx = 0;
		var sheets = {}, snames = [n];

		var refguess = {s: {r:0, c:0}, e: {r:0, c:0} };

		if(d[2] == 0x02) o.Enum = WK1Enum;
		else if(d[2] == 0x1a) o.Enum = WK3Enum;
		else if(d[2] == 0x0e) { o.Enum = WK3Enum; o.qpro = true; d.l = 0; }
		else throw new Error("Unrecognized LOTUS BOF " + d[2]);
		lotushopper(d, function(val, Rn, RT) {
			if(d[2] == 0x02) switch(RT) {
				case 0x00:
					o.vers = val;
					if(val >= 0x1000) o.qpro = true;
					break;
				case 0x06: refguess = val; break; /* RANGE */
				case 0x0F: /* LABEL */
					if(!o.qpro) val[1].v = val[1].v.substr(1);
					/* falls through */
				case 0x0D: /* INTEGER */
				case 0x0E: /* NUMBER */
				case 0x10: /* FORMULA */
				case 0x33: /* STRING */
					/* TODO: actual translation of the format code */
					if(RT == 0x0E && (val[2] & 0x70) == 0x70 && (val[2] & 0x0F) > 1 && (val[2] & 0x0F) < 15) {
						val[1].z = o.dateNF || SSF._table[14];
						if(o.cellDates) { val[1].t = 'd'; val[1].v = numdate(val[1].v); }
					}
					if(o.dense) {
						if(!s[val[0].r]) s[val[0].r] = [];
						s[val[0].r][val[0].c] = val[1];
					} else s[encode_cell(val[0])] = val[1];
					break;
			} else switch(RT) {
				case 0x16: /* LABEL16 */
					val[1].v = val[1].v.substr(1);
					/* falls through */
				case 0x17: /* NUMBER17 */
				case 0x18: /* NUMBER18 */
				case 0x19: /* FORMULA19 */
				case 0x25: /* NUMBER25 */
				case 0x27: /* NUMBER27 */
				case 0x28: /* FORMULA28 */
					if(val[3] > sidx) {
						s["!ref"] = encode_range(refguess);
						sheets[n] = s;
						s = (o.dense ? [] : {});
						refguess = {s: {r:0, c:0}, e: {r:0, c:0} };
						sidx = val[3]; n = "Sheet" + (sidx + 1);
						snames.push(n);
					}
					s[encode_cell(val[0])] = val[1];
					if(refguess.e.c < val[0].c) refguess.e.c = val[0].c;
					if(refguess.e.r < val[0].r) refguess.e.r = val[0].r;
					break;
				default: break;
			}
		}, o);

		s["!ref"] = encode_range(refguess);
		sheets[n] = s;
		return { SheetNames: snames, Sheets:sheets };
	}

	function parse_RANGE(blob, length) {
		var o = {s:{c:0,r:0},e:{c:0,r:0}};
		o.s.c = blob.read_shift(2);
		o.s.r = blob.read_shift(2);
		o.e.c = blob.read_shift(2);
		o.e.r = blob.read_shift(2);
		if(o.s.c == 0xFFFF) o.s.c = o.e.c = o.s.r = o.e.r = 0;
		return o;
	}

	function parse_cell(blob, length, opts) {
		var o = [{c:0,r:0}, {t:'n',v:0}, 0];
		if(opts.qpro && opts.vers != 0x5120) {
			o[0].c = blob.read_shift(1);
			blob.l++;
			o[0].r = blob.read_shift(2);
			blob.l+=2;
		} else {
			o[2] = blob.read_shift(1);
			o[0].c = blob.read_shift(2); o[0].r = blob.read_shift(2);
		}
		return o;
	}

	function parse_LABEL(blob, length, opts) {
		var tgt = blob.l + length;
		var o = parse_cell(blob, length, opts);
		o[1].t = 's';
		if(opts.vers == 0x5120) {
			blob.l++;
			var len = blob.read_shift(1);
			o[1].v = blob.read_shift(len, 'utf8');
			return o;
		}
		if(opts.qpro) blob.l++;
		o[1].v = blob.read_shift(tgt - blob.l, 'cstr');
		return o;
	}

	function parse_INTEGER(blob, length, opts) {
		var o = parse_cell(blob, length, opts);
		o[1].v = blob.read_shift(2, 'i');
		return o;
	}

	function parse_NUMBER(blob, length, opts) {
		var o = parse_cell(blob, length, opts);
		o[1].v = blob.read_shift(8, 'f');
		return o;
	}

	function parse_FORMULA(blob, length, opts) {
		var tgt = blob.l + length;
		var o = parse_cell(blob, length, opts);
		/* TODO: formula */
		o[1].v = blob.read_shift(8, 'f');
		if(opts.qpro) blob.l = tgt;
		else {
			var flen = blob.read_shift(2);
			blob.l += flen;
		}
		return o;
	}

	function parse_cell_3(blob, length) {
		var o = [{c:0,r:0}, {t:'n',v:0}, 0];
		o[0].r = blob.read_shift(2); o[3] = blob[blob.l++]; o[0].c = blob[blob.l++];
		return o;
	}

	function parse_LABEL_16(blob, length) {
		var o = parse_cell_3(blob, length);
		o[1].t = 's';
		o[1].v = blob.read_shift(length - 4, 'cstr');
		return o;
	}

	function parse_NUMBER_18(blob, length) {
		var o = parse_cell_3(blob, length);
		o[1].v = blob.read_shift(2);
		var v = o[1].v >> 1;
		/* TODO: figure out all of the corner cases */
		if(o[1].v & 0x1) {
			switch(v & 0x07) {
				case 1: v = (v >> 3) * 500; break;
				case 2: v = (v >> 3) / 20; break;
				case 4: v = (v >> 3) / 2000; break;
				case 6: v = (v >> 3) / 16; break;
				case 7: v = (v >> 3) / 64; break;
				default: throw "unknown NUMBER_18 encoding " + (v & 0x07);
			}
		}
		o[1].v = v;
		return o;
	}

	function parse_NUMBER_17(blob, length) {
		var o = parse_cell_3(blob, length);
		var v1 = blob.read_shift(4);
		var v2 = blob.read_shift(4);
		var e = blob.read_shift(2);
		if(e == 0xFFFF) { o[1].v = 0; return o; }
		var s = e & 0x8000; e = (e&0x7FFF) - 16446;
		o[1].v = ((e > 0 ? (v2 << e) : (v2 >>> -e)) + (e > -32 ? (v1 << (e + 32)) : (v1 >>> -(e + 32))));
		return o;
	}

	function parse_FORMULA_19(blob, length) {
		var o = parse_NUMBER_17(blob, 14);
		blob.l += length - 14; /* TODO: formula */
		return o;
	}

	function parse_NUMBER_25(blob, length) {
		var o = parse_cell_3(blob, length);
		var v1 = blob.read_shift(4);
		o[1].v = v1 >> 6;
		return o;
	}

	function parse_NUMBER_27(blob, length) {
		var o = parse_cell_3(blob, length);
		var v1 = blob.read_shift(8,'f');
		o[1].v = v1;
		return o;
	}

	function parse_FORMULA_28(blob, length) {
		var o = parse_NUMBER_27(blob, 14);
		blob.l += length - 10; /* TODO: formula */
		return o;
	}

	var WK1Enum = {
0x0000: { n:"BOF", f:parseuint16 },
0x0001: { n:"EOF", f:parsenoop },
0x0002: { n:"CALCMODE", f:parsenoop },
0x0003: { n:"CALCORDER", f:parsenoop },
0x0004: { n:"SPLIT", f:parsenoop },
0x0005: { n:"SYNC", f:parsenoop },
0x0006: { n:"RANGE", f:parse_RANGE },
0x0007: { n:"WINDOW1", f:parsenoop },
0x0008: { n:"COLW1", f:parsenoop },
0x0009: { n:"WINTWO", f:parsenoop },
0x000A: { n:"COLW2", f:parsenoop },
0x000B: { n:"NAME", f:parsenoop },
0x000C: { n:"BLANK", f:parsenoop },
0x000D: { n:"INTEGER", f:parse_INTEGER },
0x000E: { n:"NUMBER", f:parse_NUMBER },
0x000F: { n:"LABEL", f:parse_LABEL },
0x0010: { n:"FORMULA", f:parse_FORMULA },
0x0018: { n:"TABLE", f:parsenoop },
0x0019: { n:"ORANGE", f:parsenoop },
0x001A: { n:"PRANGE", f:parsenoop },
0x001B: { n:"SRANGE", f:parsenoop },
0x001C: { n:"FRANGE", f:parsenoop },
0x001D: { n:"KRANGE1", f:parsenoop },
0x0020: { n:"HRANGE", f:parsenoop },
0x0023: { n:"KRANGE2", f:parsenoop },
0x0024: { n:"PROTEC", f:parsenoop },
0x0025: { n:"FOOTER", f:parsenoop },
0x0026: { n:"HEADER", f:parsenoop },
0x0027: { n:"SETUP", f:parsenoop },
0x0028: { n:"MARGINS", f:parsenoop },
0x0029: { n:"LABELFMT", f:parsenoop },
0x002A: { n:"TITLES", f:parsenoop },
0x002B: { n:"SHEETJS", f:parsenoop },
0x002D: { n:"GRAPH", f:parsenoop },
0x002E: { n:"NGRAPH", f:parsenoop },
0x002F: { n:"CALCCOUNT", f:parsenoop },
0x0030: { n:"UNFORMATTED", f:parsenoop },
0x0031: { n:"CURSORW12", f:parsenoop },
0x0032: { n:"WINDOW", f:parsenoop },
0x0033: { n:"STRING", f:parse_LABEL },
0x0037: { n:"PASSWORD", f:parsenoop },
0x0038: { n:"LOCKED", f:parsenoop },
0x003C: { n:"QUERY", f:parsenoop },
0x003D: { n:"QUERYNAME", f:parsenoop },
0x003E: { n:"PRINT", f:parsenoop },
0x003F: { n:"PRINTNAME", f:parsenoop },
0x0040: { n:"GRAPH2", f:parsenoop },
0x0041: { n:"GRAPHNAME", f:parsenoop },
0x0042: { n:"ZOOM", f:parsenoop },
0x0043: { n:"SYMSPLIT", f:parsenoop },
0x0044: { n:"NSROWS", f:parsenoop },
0x0045: { n:"NSCOLS", f:parsenoop },
0x0046: { n:"RULER", f:parsenoop },
0x0047: { n:"NNAME", f:parsenoop },
0x0048: { n:"ACOMM", f:parsenoop },
0x0049: { n:"AMACRO", f:parsenoop },
0x004A: { n:"PARSE", f:parsenoop },
0x00FF: { n:"", f:parsenoop }
	};

	var WK3Enum = {
0x0000: { n:"BOF", f:parsenoop },
0x0001: { n:"EOF", f:parsenoop },
0x0003: { n:"??", f:parsenoop },
0x0004: { n:"??", f:parsenoop },
0x0005: { n:"??", f:parsenoop },
0x0006: { n:"??", f:parsenoop },
0x0007: { n:"??", f:parsenoop },
0x0009: { n:"??", f:parsenoop },
0x000a: { n:"??", f:parsenoop },
0x000b: { n:"??", f:parsenoop },
0x000c: { n:"??", f:parsenoop },
0x000e: { n:"??", f:parsenoop },
0x000f: { n:"??", f:parsenoop },
0x0010: { n:"??", f:parsenoop },
0x0011: { n:"??", f:parsenoop },
0x0012: { n:"??", f:parsenoop },
0x0013: { n:"??", f:parsenoop },
0x0015: { n:"??", f:parsenoop },
0x0016: { n:"LABEL16", f:parse_LABEL_16},
0x0017: { n:"NUMBER17", f:parse_NUMBER_17 },
0x0018: { n:"NUMBER18", f:parse_NUMBER_18 },
0x0019: { n:"FORMULA19", f:parse_FORMULA_19},
0x001a: { n:"??", f:parsenoop },
0x001b: { n:"??", f:parsenoop },
0x001c: { n:"??", f:parsenoop },
0x001d: { n:"??", f:parsenoop },
0x001e: { n:"??", f:parsenoop },
0x001f: { n:"??", f:parsenoop },
0x0021: { n:"??", f:parsenoop },
0x0025: { n:"NUMBER25", f:parse_NUMBER_25 },
0x0027: { n:"NUMBER27", f:parse_NUMBER_27 },
0x0028: { n:"FORMULA28", f:parse_FORMULA_28 },
0x00FF: { n:"", f:parsenoop }
	};
	return {
		to_workbook: lotus_to_workbook
	};
})();
/* 18.4.1 charset to codepage mapping */
var CS2CP = ({
0:    1252, /* ANSI */
1:   65001, /* DEFAULT */
2:   65001, /* SYMBOL */
77:  10000, /* MAC */
128:   932, /* SHIFTJIS */
129:   949, /* HANGUL */
130:  1361, /* JOHAB */
134:   936, /* GB2312 */
136:   950, /* CHINESEBIG5 */
161:  1253, /* GREEK */
162:  1254, /* TURKISH */
163:  1258, /* VIETNAMESE */
177:  1255, /* HEBREW */
178:  1256, /* ARABIC */
186:  1257, /* BALTIC */
204:  1251, /* RUSSIAN */
222:   874, /* THAI */
238:  1250, /* EASTEUROPE */
255:  1252, /* OEM */
69:   6969  /* MISC */
});

/* Parse a list of <r> tags */
var parse_rs = (function parse_rs_factory() {
	var tregex = matchtag("t"), rpregex = matchtag("rPr"), rregex = /<(?:\w+:)?r>/g, rend = /<\/(?:\w+:)?r>/, nlregex = /\r\n/g;
	/* 18.4.7 rPr CT_RPrElt */
	var parse_rpr = function parse_rpr(rpr, intro, outro) {
		var font = {}, cp = 65001, align = "";
		var m = rpr.match(tagregex), i = 0;
		if(m) for(;i!=m.length; ++i) {
			var y = parsexmltag(m[i]);
			switch(y[0].replace(/\w*:/g,"")) {
				/* 18.8.12 condense CT_BooleanProperty */
				/* ** not required . */
				case '<condense': break;
				/* 18.8.17 extend CT_BooleanProperty */
				/* ** not required . */
				case '<extend': break;
				/* 18.8.36 shadow CT_BooleanProperty */
				/* ** not required . */
				case '<shadow':
					if(!y.val) break;
					/* falls through */
				case '<shadow>':
				case '<shadow/>': font.shadow = 1; break;
				case '</shadow>': break;

				/* 18.4.1 charset CT_IntProperty TODO */
				case '<charset':
					if(y.val == '1') break;
					cp = CS2CP[parseInt(y.val, 10)];
					break;

				/* 18.4.2 outline CT_BooleanProperty TODO */
				case '<outline':
					if(!y.val) break;
					/* falls through */
				case '<outline>':
				case '<outline/>': font.outline = 1; break;
				case '</outline>': break;

				/* 18.4.5 rFont CT_FontName */
				case '<rFont': font.name = y.val; break;

				/* 18.4.11 sz CT_FontSize */
				case '<sz': font.sz = y.val; break;

				/* 18.4.10 strike CT_BooleanProperty */
				case '<strike':
					if(!y.val) break;
					/* falls through */
				case '<strike>':
				case '<strike/>': font.strike = 1; break;
				case '</strike>': break;

				/* 18.4.13 u CT_UnderlineProperty */
				case '<u':
					if(!y.val) break;
					switch(y.val) {
						case 'double': font.uval = "double"; break;
						case 'singleAccounting': font.uval = "single-accounting"; break;
						case 'doubleAccounting': font.uval = "double-accounting"; break;
					}
					/* falls through */
				case '<u>':
				case '<u/>': font.u = 1; break;
				case '</u>': break;

				/* 18.8.2 b */
				case '<b':
					if(y.val == '0') break;
					/* falls through */
				case '<b>':
				case '<b/>': font.b = 1; break;
				case '</b>': break;

				/* 18.8.26 i */
				case '<i':
					if(y.val == '0') break;
					/* falls through */
				case '<i>':
				case '<i/>': font.i = 1; break;
				case '</i>': break;

				/* 18.3.1.15 color CT_Color TODO: tint, theme, auto, indexed */
				case '<color':
					if(y.rgb) font.color = y.rgb.substr(2,6);
					break;

				/* 18.8.18 family ST_FontFamily */
				case '<family': font.family = y.val; break;

				/* 18.4.14 vertAlign CT_VerticalAlignFontProperty TODO */
				case '<vertAlign': align = y.val; break;

				/* 18.8.35 scheme CT_FontScheme TODO */
				case '<scheme': break;

				default:
					if(y[0].charCodeAt(1) !== 47) throw 'Unrecognized rich format ' + y[0];
			}
		}
		var style = [];

		if(font.u) style.push("text-decoration: underline;");
		if(font.uval) style.push("text-underline-style:" + font.uval + ";");
		if(font.sz) style.push("font-size:" + font.sz + ";");
		if(font.outline) style.push("text-effect: outline;");
		if(font.shadow) style.push("text-shadow: auto;");
		intro.push('<span style="' + style.join("") + '">');

		if(font.b) { intro.push("<b>"); outro.push("</b>"); }
		if(font.i) { intro.push("<i>"); outro.push("</i>"); }
		if(font.strike) { intro.push("<s>"); outro.push("</s>"); }

		if(align == "superscript") align = "sup";
		else if(align == "subscript") align = "sub";
		if(align != "") { intro.push("<" + align + ">"); outro.push("</" + align + ">"); }

		outro.push("</span>");
		return cp;
	};

	/* 18.4.4 r CT_RElt */
	function parse_r(r) {
		var terms = [[],"",[]];
		/* 18.4.12 t ST_Xstring */
		var t = r.match(tregex), cp = 65001;
		if(!isval(t)) return "";
		terms[1] = t[1];

		var rpr = r.match(rpregex);
		if(isval(rpr)) cp = parse_rpr(rpr[1], terms[0], terms[2]);

		return terms[0].join("") + terms[1].replace(nlregex,'<br/>') + terms[2].join("");
	}
	return function parse_rs(rs) {
		return rs.replace(rregex,"").split(rend).map(parse_r).join("");
	};
})();

/* 18.4.8 si CT_Rst */
var sitregex = /<(?:\w+:)?t[^>]*>([^<]*)<\/(?:\w+:)?t>/g, sirregex = /<(?:\w+:)?r>/;
var sirphregex = /<(?:\w+:)?rPh.*?>(.*?)<\/(?:\w+:)?rPh>/g;
function parse_si(x, opts) {
	var html = opts ? opts.cellHTML : true;
	var z = {};
	if(!x) return null;
	var y;
	/* 18.4.12 t ST_Xstring (Plaintext String) */
	// TODO: is whitespace actually valid here?
	if(x.match(/^\s*<(?:\w+:)?t[^>]*>/)) {
		z.t = utf8read(unescapexml(x.substr(x.indexOf(">")+1).split(/<\/(?:\w+:)?t>/)[0]));
		z.r = utf8read(x);
		if(html) z.h = escapehtml(z.t);
	}
	/* 18.4.4 r CT_RElt (Rich Text Run) */
	else if((y = x.match(sirregex))) {
		z.r = utf8read(x);
		z.t = utf8read(unescapexml((x.replace(sirphregex, '').match(sitregex)||[]).join("").replace(tagregex,"")));
		if(html) z.h = parse_rs(z.r);
	}
	/* 18.4.3 phoneticPr CT_PhoneticPr (TODO: needed for Asian support) */
	/* 18.4.6 rPh CT_PhoneticRun (TODO: needed for Asian support) */
	return z;
}

/* 18.4 Shared String Table */
var sstr0 = /<(?:\w+:)?sst([^>]*)>([\s\S]*)<\/(?:\w+:)?sst>/;
var sstr1 = /<(?:\w+:)?(?:si|sstItem)>/g;
var sstr2 = /<\/(?:\w+:)?(?:si|sstItem)>/;
function parse_sst_xml(data, opts) {
	var s = ([]), ss = "";
	if(!data) return s;
	/* 18.4.9 sst CT_Sst */
	var sst = data.match(sstr0);
	if(isval(sst)) {
		ss = sst[2].replace(sstr1,"").split(sstr2);
		for(var i = 0; i != ss.length; ++i) {
			var o = parse_si(ss[i].trim(), opts);
			if(o != null) s[s.length] = o;
		}
		sst = parsexmltag(sst[1]); s.Count = sst.count; s.Unique = sst.uniqueCount;
	}
	return s;
}

RELS.SST = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings";
var straywsregex = /^\s|\s$|[\t\n\r]/;
function write_sst_xml(sst, opts) {
	if(!opts.bookSST) return "";
	var o = [XML_HEADER];
	o[o.length] = (writextag('sst', null, {
		xmlns: XMLNS.main[0],
		count: sst.Count,
		uniqueCount: sst.Unique
	}));
	for(var i = 0; i != sst.length; ++i) { if(sst[i] == null) continue;
		var s = sst[i];
		var sitag = "<si>";
		if(s.r) sitag += s.r;
		else {
			sitag += "<t";
			if(!s.t) s.t = "";
			if(s.t.match(straywsregex)) sitag += ' xml:space="preserve"';
			sitag += ">" + escapexml(s.t) + "</t>";
		}
		sitag += "</si>";
		o[o.length] = (sitag);
	}
	if(o.length>2){ o[o.length] = ('</sst>'); o[1]=o[1].replace("/>",">"); }
	return o.join("");
}
/* [MS-XLSB] 2.4.219 BrtBeginSst */
function parse_BrtBeginSst(data, length) {
	return [data.read_shift(4), data.read_shift(4)];
}

/* [MS-XLSB] 2.1.7.45 Shared Strings */
function parse_sst_bin(data, opts) {
	var s = ([]);
	var pass = false;
	recordhopper(data, function hopper_sst(val, R_n, RT) {
		switch(RT) {
			case 0x009F: /* 'BrtBeginSst' */
				s.Count = val[0]; s.Unique = val[1]; break;
			case 0x0013: /* 'BrtSSTItem' */
				s.push(val); break;
			case 0x00A0: /* 'BrtEndSst' */
				return true;

			case 0x0023: /* 'BrtFRTBegin' */
				pass = true; break;
			case 0x0024: /* 'BrtFRTEnd' */
				pass = false; break;

			default:
				if(R_n.indexOf("Begin") > 0){/* empty */}
				else if(R_n.indexOf("End") > 0){/* empty */}
				if(!pass || opts.WTF) throw new Error("Unexpected record " + RT + " " + R_n);
		}
	});
	return s;
}

function write_BrtBeginSst(sst, o) {
	if(!o) o = new_buf(8);
	o.write_shift(4, sst.Count);
	o.write_shift(4, sst.Unique);
	return o;
}

var write_BrtSSTItem = write_RichStr;

function write_sst_bin(sst, opts) {
	var ba = buf_array();
	write_record(ba, "BrtBeginSst", write_BrtBeginSst(sst));
	for(var i = 0; i < sst.length; ++i) write_record(ba, "BrtSSTItem", write_BrtSSTItem(sst[i]));
	/* FRTSST */
	write_record(ba, "BrtEndSst");
	return ba.end();
}
function _JS2ANSI(str) {
	if(typeof cptable !== 'undefined') return cptable.utils.encode(1252, str);
	var o = [], oo = str.split("");
	for(var i = 0; i < oo.length; ++i) o[i] = oo[i].charCodeAt(0);
	return o;
}

/* [MS-OFFCRYPTO] 2.1.4 Version */
function parse_CRYPTOVersion(blob, length) {
	var o = {};
	o.Major = blob.read_shift(2);
	o.Minor = blob.read_shift(2);
if(length >= 4) blob.l += length - 4;
	return o;
}

/* [MS-OFFCRYPTO] 2.1.5 DataSpaceVersionInfo */
function parse_DataSpaceVersionInfo(blob, length) {
	var o = {};
	o.id = blob.read_shift(0, 'lpp4');
	o.R = parse_CRYPTOVersion(blob, 4);
	o.U = parse_CRYPTOVersion(blob, 4);
	o.W = parse_CRYPTOVersion(blob, 4);
	return o;
}

/* [MS-OFFCRYPTO] 2.1.6.1 DataSpaceMapEntry Structure */
function parse_DataSpaceMapEntry(blob) {
	var len = blob.read_shift(4);
	var end = blob.l + len - 4;
	var o = {};
	var cnt = blob.read_shift(4);
	var comps = [];
	while(cnt-- > 0) {
		/* [MS-OFFCRYPTO] 2.1.6.2 DataSpaceReferenceComponent Structure */
		var rc = {};
		rc.t = blob.read_shift(4);
		rc.v = blob.read_shift(0, 'lpp4');
		comps.push(rc);
	}
	o.name = blob.read_shift(0, 'lpp4');
	o.comps = comps;
	return o;
}

/* [MS-OFFCRYPTO] 2.1.6 DataSpaceMap */
function parse_DataSpaceMap(blob, length) {
	var o = [];
	blob.l += 4; // must be 0x8
	var cnt = blob.read_shift(4);
	while(cnt-- > 0) o.push(parse_DataSpaceMapEntry(blob));
	return o;
}

/* [MS-OFFCRYPTO] 2.1.7 DataSpaceDefinition */
function parse_DataSpaceDefinition(blob, length) {
	var o = [];
	blob.l += 4; // must be 0x8
	var cnt = blob.read_shift(4);
	while(cnt-- > 0) o.push(blob.read_shift(0, 'lpp4'));
	return o;
}

/* [MS-OFFCRYPTO] 2.1.8 DataSpaceDefinition */
function parse_TransformInfoHeader(blob, length) {
	var o = {};
	var len = blob.read_shift(4);
	var tgt = blob.l + len - 4;
	blob.l += 4; // must be 0x1
	o.id = blob.read_shift(0, 'lpp4');
	// tgt == len
	o.name = blob.read_shift(0, 'lpp4');
	o.R = parse_CRYPTOVersion(blob, 4);
	o.U = parse_CRYPTOVersion(blob, 4);
	o.W = parse_CRYPTOVersion(blob, 4);
	return o;
}

function parse_Primary(blob, length) {
	/* [MS-OFFCRYPTO] 2.2.6 IRMDSTransformInfo */
	var hdr = parse_TransformInfoHeader(blob);
	/* [MS-OFFCRYPTO] 2.1.9 EncryptionTransformInfo */
	hdr.ename = blob.read_shift(0, '8lpp4');
	hdr.blksz = blob.read_shift(4);
	hdr.cmode = blob.read_shift(4);
	if(blob.read_shift(4) != 0x04) throw new Error("Bad !Primary record");
	return hdr;
}

/* [MS-OFFCRYPTO] 2.3.2 Encryption Header */
function parse_EncryptionHeader(blob, length) {
	var tgt = blob.l + length;
	var o = {};
	o.Flags = (blob.read_shift(4) & 0x3F);
	blob.l += 4;
	o.AlgID = blob.read_shift(4);
	var valid = false;
	switch(o.AlgID) {
		case 0x660E: case 0x660F: case 0x6610: valid = (o.Flags == 0x24); break;
		case 0x6801: valid = (o.Flags == 0x04); break;
		case 0: valid = (o.Flags == 0x10 || o.Flags == 0x04 || o.Flags == 0x24); break;
		default: throw 'Unrecognized encryption algorithm: ' + o.AlgID;
	}
	if(!valid) throw new Error("Encryption Flags/AlgID mismatch");
	o.AlgIDHash = blob.read_shift(4);
	o.KeySize = blob.read_shift(4);
	o.ProviderType = blob.read_shift(4);
	blob.l += 8;
	o.CSPName = blob.read_shift((tgt-blob.l)>>1, 'utf16le').slice(0,-1);
	blob.l = tgt;
	return o;
}

/* [MS-OFFCRYPTO] 2.3.3 Encryption Verifier */
function parse_EncryptionVerifier(blob, length) {
	var o = {};
	blob.l += 4; // SaltSize must be 0x10
	o.Salt = blob.slice(blob.l, blob.l+16); blob.l += 16;
	o.Verifier = blob.slice(blob.l, blob.l+16); blob.l += 16;
	var sz = blob.read_shift(4);
	o.VerifierHash = blob.slice(blob.l, blob.l + sz); blob.l += sz;
	return o;
}

/* [MS-OFFCRYPTO] 2.3.4.* EncryptionInfo Stream */
function parse_EncryptionInfo(blob, length) {
	var vers = parse_CRYPTOVersion(blob);
	switch(vers.Minor) {
		case 0x02: return parse_EncInfoStd(blob, vers);
		case 0x03: return parse_EncInfoExt(blob, vers);
		case 0x04: return parse_EncInfoAgl(blob, vers);
	}
	throw new Error("ECMA-376 Encryped file unrecognized Version: " + vers.Minor);
}

/* [MS-OFFCRYPTO] 2.3.4.5  EncryptionInfo Stream (Standard Encryption) */
function parse_EncInfoStd(blob, vers) {
	var flags = blob.read_shift(4);
	if((flags & 0x3F) != 0x24) throw new Error("EncryptionInfo mismatch");
	var sz = blob.read_shift(4);
	var tgt = blob.l + sz;
	var hdr = parse_EncryptionHeader(blob, sz);
	var verifier = parse_EncryptionVerifier(blob, blob.length - blob.l);
	return { t:"Std", h:hdr, v:verifier };
}
/* [MS-OFFCRYPTO] 2.3.4.6  EncryptionInfo Stream (Extensible Encryption) */
function parse_EncInfoExt(blob, vers) { throw new Error("File is password-protected: ECMA-376 Extensible"); }
/* [MS-OFFCRYPTO] 2.3.4.10 EncryptionInfo Stream (Agile Encryption) */
function parse_EncInfoAgl(blob, vers) { throw new Error("File is password-protected: ECMA-376 Agile"); }




/* [MS-OFFCRYPTO] 2.3.5.1 RC4 CryptoAPI Encryption Header */
function parse_RC4CryptoHeader(blob, length) {
	var o = {};
	var vers = o.EncryptionVersionInfo = parse_CRYPTOVersion(blob, 4); length -= 4;
	if(vers.Minor != 2) throw 'unrecognized minor version code: ' + vers.Minor;
	if(vers.Major > 4 || vers.Major < 2) throw 'unrecognized major version code: ' + vers.Major;
	o.Flags = blob.read_shift(4); length -= 4;
	var sz = blob.read_shift(4); length -= 4;
	o.EncryptionHeader = parse_EncryptionHeader(blob, sz); length -= sz;
	o.EncryptionVerifier = parse_EncryptionVerifier(blob, length);
	return o;
}
/* [MS-OFFCRYPTO] 2.3.6.1 RC4 Encryption Header */
function parse_RC4Header(blob, length) {
	var o = {};
	var vers = o.EncryptionVersionInfo = parse_CRYPTOVersion(blob, 4); length -= 4;
	if(vers.Major != 1 || vers.Minor != 1) throw 'unrecognized version code ' + vers.Major + ' : ' + vers.Minor;
	o.Salt = blob.read_shift(16);
	o.EncryptedVerifier = blob.read_shift(16);
	o.EncryptedVerifierHash = blob.read_shift(16);
	return o;
}

/* [MS-OFFCRYPTO] 2.3.7.1 Binary Document Password Verifier Derivation */
function crypto_CreatePasswordVerifier_Method1(Password) {
	var Verifier = 0x0000, PasswordArray;
	var PasswordDecoded = _JS2ANSI(Password);
	var len = PasswordDecoded.length + 1, i, PasswordByte;
	var Intermediate1, Intermediate2, Intermediate3;
	PasswordArray = new_raw_buf(len);
	PasswordArray[0] = PasswordDecoded.length;
	for(i = 1; i != len; ++i) PasswordArray[i] = PasswordDecoded[i-1];
	for(i = len-1; i >= 0; --i) {
		PasswordByte = PasswordArray[i];
		Intermediate1 = ((Verifier & 0x4000) === 0x0000) ? 0 : 1;
		Intermediate2 = (Verifier << 1) & 0x7FFF;
		Intermediate3 = Intermediate1 | Intermediate2;
		Verifier = Intermediate3 ^ PasswordByte;
	}
	return Verifier ^ 0xCE4B;
}

/* [MS-OFFCRYPTO] 2.3.7.2 Binary Document XOR Array Initialization */
var crypto_CreateXorArray_Method1 = (function() {
	var PadArray = [0xBB, 0xFF, 0xFF, 0xBA, 0xFF, 0xFF, 0xB9, 0x80, 0x00, 0xBE, 0x0F, 0x00, 0xBF, 0x0F, 0x00];
	var InitialCode = [0xE1F0, 0x1D0F, 0xCC9C, 0x84C0, 0x110C, 0x0E10, 0xF1CE, 0x313E, 0x1872, 0xE139, 0xD40F, 0x84F9, 0x280C, 0xA96A, 0x4EC3];
	var XorMatrix = [0xAEFC, 0x4DD9, 0x9BB2, 0x2745, 0x4E8A, 0x9D14, 0x2A09, 0x7B61, 0xF6C2, 0xFDA5, 0xEB6B, 0xC6F7, 0x9DCF, 0x2BBF, 0x4563, 0x8AC6, 0x05AD, 0x0B5A, 0x16B4, 0x2D68, 0x5AD0, 0x0375, 0x06EA, 0x0DD4, 0x1BA8, 0x3750, 0x6EA0, 0xDD40, 0xD849, 0xA0B3, 0x5147, 0xA28E, 0x553D, 0xAA7A, 0x44D5, 0x6F45, 0xDE8A, 0xAD35, 0x4A4B, 0x9496, 0x390D, 0x721A, 0xEB23, 0xC667, 0x9CEF, 0x29FF, 0x53FE, 0xA7FC, 0x5FD9, 0x47D3, 0x8FA6, 0x0F6D, 0x1EDA, 0x3DB4, 0x7B68, 0xF6D0, 0xB861, 0x60E3, 0xC1C6, 0x93AD, 0x377B, 0x6EF6, 0xDDEC, 0x45A0, 0x8B40, 0x06A1, 0x0D42, 0x1A84, 0x3508, 0x6A10, 0xAA51, 0x4483, 0x8906, 0x022D, 0x045A, 0x08B4, 0x1168, 0x76B4, 0xED68, 0xCAF1, 0x85C3, 0x1BA7, 0x374E, 0x6E9C, 0x3730, 0x6E60, 0xDCC0, 0xA9A1, 0x4363, 0x86C6, 0x1DAD, 0x3331, 0x6662, 0xCCC4, 0x89A9, 0x0373, 0x06E6, 0x0DCC, 0x1021, 0x2042, 0x4084, 0x8108, 0x1231, 0x2462, 0x48C4];
	var Ror = function(Byte) { return ((Byte/2) | (Byte*128)) & 0xFF; };
	var XorRor = function(byte1, byte2) { return Ror(byte1 ^ byte2); };
	var CreateXorKey_Method1 = function(Password) {
		var XorKey = InitialCode[Password.length - 1];
		var CurrentElement = 0x68;
		for(var i = Password.length-1; i >= 0; --i) {
			var Char = Password[i];
			for(var j = 0; j != 7; ++j) {
				if(Char & 0x40) XorKey ^= XorMatrix[CurrentElement];
				Char *= 2; --CurrentElement;
			}
		}
		return XorKey;
	};
	return function(password) {
		var Password = _JS2ANSI(password);
		var XorKey = CreateXorKey_Method1(Password);
		var Index = Password.length;
		var ObfuscationArray = new_raw_buf(16);
		for(var i = 0; i != 16; ++i) ObfuscationArray[i] = 0x00;
		var Temp, PasswordLastChar, PadIndex;
		if((Index & 1) === 1) {
			Temp = XorKey >> 8;
			ObfuscationArray[Index] = XorRor(PadArray[0], Temp);
			--Index;
			Temp = XorKey & 0xFF;
			PasswordLastChar = Password[Password.length - 1];
			ObfuscationArray[Index] = XorRor(PasswordLastChar, Temp);
		}
		while(Index > 0) {
			--Index;
			Temp = XorKey >> 8;
			ObfuscationArray[Index] = XorRor(Password[Index], Temp);
			--Index;
			Temp = XorKey & 0xFF;
			ObfuscationArray[Index] = XorRor(Password[Index], Temp);
		}
		Index = 15;
		PadIndex = 15 - Password.length;
		while(PadIndex > 0) {
			Temp = XorKey >> 8;
			ObfuscationArray[Index] = XorRor(PadArray[PadIndex], Temp);
			--Index;
			--PadIndex;
			Temp = XorKey & 0xFF;
			ObfuscationArray[Index] = XorRor(Password[Index], Temp);
			--Index;
			--PadIndex;
		}
		return ObfuscationArray;
	};
})();

/* [MS-OFFCRYPTO] 2.3.7.3 Binary Document XOR Data Transformation Method 1 */
var crypto_DecryptData_Method1 = function(password, Data, XorArrayIndex, XorArray, O) {
	/* If XorArray is set, use it; if O is not set, make changes in-place */
	if(!O) O = Data;
	if(!XorArray) XorArray = crypto_CreateXorArray_Method1(password);
	var Index, Value;
	for(Index = 0; Index != Data.length; ++Index) {
		Value = Data[Index];
		Value ^= XorArray[XorArrayIndex];
		Value = ((Value>>5) | (Value<<3)) & 0xFF;
		O[Index] = Value;
		++XorArrayIndex;
	}
	return [O, XorArrayIndex, XorArray];
};

var crypto_MakeXorDecryptor = function(password) {
	var XorArrayIndex = 0, XorArray = crypto_CreateXorArray_Method1(password);
	return function(Data) {
		var O = crypto_DecryptData_Method1("", Data, XorArrayIndex, XorArray);
		XorArrayIndex = O[1];
		return O[0];
	};
};

/* 2.5.343 */
function parse_XORObfuscation(blob, length, opts, out) {
	var o = ({ key: parseuint16(blob), verificationBytes: parseuint16(blob) });
	if(opts.password) o.verifier = crypto_CreatePasswordVerifier_Method1(opts.password);
	out.valid = o.verificationBytes === o.verifier;
	if(out.valid) out.insitu_decrypt = crypto_MakeXorDecryptor(opts.password);
	return o;
}

/* 2.4.117 */
function parse_FilePassHeader(blob, length, oo) {
	var o = oo || {}; o.Info = blob.read_shift(2); blob.l -= 2;
	if(o.Info === 1) o.Data = parse_RC4Header(blob, length);
	else o.Data = parse_RC4CryptoHeader(blob, length);
	return o;
}
function parse_FilePass(blob, length, opts) {
	var o = { Type: blob.read_shift(2) }; /* wEncryptionType */
	if(o.Type) parse_FilePassHeader(blob, length-2, o);
	else parse_XORObfuscation(blob, length-2, opts, o);
	return o;
}


function hex2RGB(h) {
	var o = h.substr(h[0]==="#"?1:0,6);
	return [parseInt(o.substr(0,2),16),parseInt(o.substr(2,2),16),parseInt(o.substr(4,2),16)];
}
function rgb2Hex(rgb) {
	for(var i=0,o=1; i!=3; ++i) o = o*256 + (rgb[i]>255?255:rgb[i]<0?0:rgb[i]);
	return o.toString(16).toUpperCase().substr(1);
}

function rgb2HSL(rgb) {
	var R = rgb[0]/255, G = rgb[1]/255, B=rgb[2]/255;
	var M = Math.max(R, G, B), m = Math.min(R, G, B), C = M - m;
	if(C === 0) return [0, 0, R];

	var H6 = 0, S = 0, L2 = (M + m);
	S = C / (L2 > 1 ? 2 - L2 : L2);
	switch(M){
		case R: H6 = ((G - B) / C + 6)%6; break;
		case G: H6 = ((B - R) / C + 2); break;
		case B: H6 = ((R - G) / C + 4); break;
	}
	return [H6 / 6, S, L2 / 2];
}

function hsl2RGB(hsl){
	var H = hsl[0], S = hsl[1], L = hsl[2];
	var C = S * 2 * (L < 0.5 ? L : 1 - L), m = L - C/2;
	var rgb = [m,m,m], h6 = 6*H;

	var X;
	if(S !== 0) switch(h6|0) {
		case 0: case 6: X = C * h6; rgb[0] += C; rgb[1] += X; break;
		case 1: X = C * (2 - h6);   rgb[0] += X; rgb[1] += C; break;
		case 2: X = C * (h6 - 2);   rgb[1] += C; rgb[2] += X; break;
		case 3: X = C * (4 - h6);   rgb[1] += X; rgb[2] += C; break;
		case 4: X = C * (h6 - 4);   rgb[2] += C; rgb[0] += X; break;
		case 5: X = C * (6 - h6);   rgb[2] += X; rgb[0] += C; break;
	}
	for(var i = 0; i != 3; ++i) rgb[i] = Math.round(rgb[i]*255);
	return rgb;
}

/* 18.8.3 bgColor tint algorithm */
function rgb_tint(hex, tint) {
	if(tint === 0) return hex;
	var hsl = rgb2HSL(hex2RGB(hex));
	if (tint < 0) hsl[2] = hsl[2] * (1 + tint);
	else hsl[2] = 1 - (1 - hsl[2]) * (1 - tint);
	return rgb2Hex(hsl2RGB(hsl));
}

/* 18.3.1.13 width calculations */
/* [MS-OI29500] 2.1.595 Column Width & Formatting */
var DEF_MDW = 6, MAX_MDW = 15, MIN_MDW = 1, MDW = DEF_MDW;
function width2px(width) { return Math.floor(( width + (Math.round(128/MDW))/256 )* MDW ); }
function px2char(px) { return (Math.floor((px - 5)/MDW * 100 + 0.5))/100; }
function char2width(chr) { return (Math.round((chr * MDW + 5)/MDW*256))/256; }
function px2char_(px) { return (((px - 5)/MDW * 100 + 0.5))/100; }
function char2width_(chr) { return (((chr * MDW + 5)/MDW*256))/256; }
function cycle_width(collw) { return char2width(px2char(width2px(collw))); }
/* XLSX/XLSB/XLS specify width in units of MDW */
function find_mdw_colw(collw) {
	var delta = Infinity, _MDW = MIN_MDW;
	for(MDW=MIN_MDW; MDW<MAX_MDW; ++MDW) if(Math.abs(collw - cycle_width(collw)) <= delta) { delta = Math.abs(collw - cycle_width(collw)); _MDW = MDW; }
	MDW = _MDW;
}
/* XLML specifies width in terms of pixels */
function find_mdw_wpx(wpx) {
	var delta = Infinity, guess = 0, _MDW = MIN_MDW;
	for(MDW=MIN_MDW; MDW<MAX_MDW; ++MDW) {
		guess = char2width_(px2char_(wpx))*256;
		guess = (guess) % 1;
		if(guess > 0.5) guess--;
		if(Math.abs(guess) < delta) { delta = Math.abs(guess); _MDW = MDW; }
	}
	MDW = _MDW;
}

function process_col(coll) {
	if(coll.width) {
		coll.wpx = width2px(coll.width);
		coll.wch = px2char(coll.wpx);
		coll.MDW = MDW;
	} else if(coll.wpx) {
		coll.wch = px2char(coll.wpx);
		coll.width = char2width(coll.wch);
		coll.MDW = MDW;
	} else if(typeof coll.wch == 'number') {
		coll.width = char2width(coll.wch);
		coll.wpx = width2px(coll.width);
		coll.MDW = MDW;
	}
	if(coll.customWidth) delete coll.customWidth;
}

var DEF_PPI = 96, PPI = DEF_PPI;
function px2pt(px) { return px * 96 / PPI; }
function pt2px(pt) { return pt * PPI / 96; }

/* [MS-EXSPXML3] 2.4.54 ST_enmPattern */
var XLMLPatternTypeMap = {
	"None": "none",
	"Solid": "solid",
	"Gray50": "mediumGray",
	"Gray75": "darkGray",
	"Gray25": "lightGray",
	"HorzStripe": "darkHorizontal",
	"VertStripe": "darkVertical",
	"ReverseDiagStripe": "darkDown",
	"DiagStripe": "darkUp",
	"DiagCross": "darkGrid",
	"ThickDiagCross": "darkTrellis",
	"ThinHorzStripe": "lightHorizontal",
	"ThinVertStripe": "lightVertical",
	"ThinReverseDiagStripe": "lightDown",
	"ThinHorzCross": "lightGrid"
};

/* 18.8.5 borders CT_Borders */
function parse_borders(t, styles, themes, opts) {
	styles.Borders = [];
	var border = {}, sub_border = {};
	t[0].match(tagregex).forEach(function(x) {
		var y = parsexmltag(x);
		switch (y[0]) {
			case '<borders': case '<borders>': case '</borders>': break;

			/* 18.8.4 border CT_Border */
			case '<border': case '<border>':
				border = {};
				if (y.diagonalUp) { border.diagonalUp = y.diagonalUp; }
				if (y.diagonalDown) { border.diagonalDown = y.diagonalDown; }
				styles.Borders.push(border);
				break;
			case '</border>': break;

			/* note: not in spec, appears to be CT_BorderPr */
			case '<left': case '<left/>': break;
			case '</left>': break;

			/* note: not in spec, appears to be CT_BorderPr */
			case '<right': case '<right/>': break;
			case '</right>': break;

			/* 18.8.43 top CT_BorderPr */
			case '<top': case '<top/>': break;
			case '</top>': break;

			/* 18.8.6 bottom CT_BorderPr */
			case '<bottom': case '<bottom/>': break;
			case '</bottom>': break;

			/* 18.8.13 diagonal CT_BorderPr */
			case '<diagonal': case '<diagonal/>': break;
			case '</diagonal>': break;

			/* 18.8.25 horizontal CT_BorderPr */
			case '<horizontal': case '<horizontal/>': break;
			case '</horizontal>': break;

			/* 18.8.44 vertical CT_BorderPr */
			case '<vertical': case '<vertical/>': break;
			case '</vertical>': break;

			/* 18.8.37 start CT_BorderPr */
			case '<start': case '<start/>': break;
			case '</start>': break;

			/* 18.8.16 end CT_BorderPr */
			case '<end': case '<end/>': break;
			case '</end>': break;

			/* 18.8.? color CT_Color */
			case '<color': case '<color/>': break;
			case '</color>': break;

			default: if(opts && opts.WTF) throw new Error('unrecognized ' + y[0] + ' in borders');
		}
	});
}

/* 18.8.21 fills CT_Fills */
function parse_fills(t, styles, themes, opts) {
	styles.Fills = [];
	var fill = {};
	t[0].match(tagregex).forEach(function(x) {
		var y = parsexmltag(x);
		switch(y[0]) {
			case '<fills': case '<fills>': case '</fills>': break;

			/* 18.8.20 fill CT_Fill */
			case '<fill>': break;
			case '</fill>': styles.Fills.push(fill); fill = {}; break;

			/* 18.8.24 gradientFill CT_GradientFill */
			case '<gradientFill>': break;
			case '</gradientFill>': styles.Fills.push(fill); fill = {}; break;

			/* 18.8.32 patternFill CT_PatternFill */
			case '<patternFill': case '<patternFill>':
				if(y.patternType) fill.patternType = y.patternType;
				break;
			case '<patternFill/>': case '</patternFill>': break;

			/* 18.8.3 bgColor CT_Color */
			case '<bgColor':
				if(!fill.bgColor) fill.bgColor = {};
				if(y.indexed) fill.bgColor.indexed = parseInt(y.indexed, 10);
				if(y.theme) fill.bgColor.theme = parseInt(y.theme, 10);
				if(y.tint) fill.bgColor.tint = parseFloat(y.tint);
				/* Excel uses ARGB strings */
				if(y.rgb) fill.bgColor.rgb = y.rgb.slice(-6);
				break;
			case '<bgColor/>': case '</bgColor>': break;

			/* 18.8.19 fgColor CT_Color */
			case '<fgColor':
				if(!fill.fgColor) fill.fgColor = {};
				if(y.theme) fill.fgColor.theme = parseInt(y.theme, 10);
				if(y.tint) fill.fgColor.tint = parseFloat(y.tint);
				/* Excel uses ARGB strings */
				if(y.rgb) fill.fgColor.rgb = y.rgb.slice(-6);
				break;
			case '<fgColor/>': case '</fgColor>': break;

			/* 18.8.38 stop CT_GradientStop */
			case '<stop': case '<stop/>': break;
			case '</stop>': break;

			/* 18.8.? color CT_Color */
			case '<color': case '<color/>': break;
			case '</color>': break;

			default: if(opts && opts.WTF) throw new Error('unrecognized ' + y[0] + ' in fills');
		}
	});
}

/* 18.8.23 fonts CT_Fonts */
function parse_fonts(t, styles, themes, opts) {
	styles.Fonts = [];
	var font = {};
	t[0].match(tagregex).forEach(function(x) {
		var y = parsexmltag(x);
		switch (y[0]) {
			case '<fonts': case '<fonts>': case '</fonts>': break;

			/* 18.8.22 font CT_Font */
			case '<font': case '<font>': break;
			case '</font>': case '<font/>':
				styles.Fonts.push(font);
				font = {};
				break;

			/* 18.8.29 name CT_FontName */
			case '<name': if(y.val) font.name = y.val; break;
			case '<name/>': case '</name>': break;

			/* 18.8.2  b CT_BooleanProperty */
			case '<b': font.bold = y.val ? parsexmlbool(y.val) : 1; break;
			case '<b/>': font.bold = 1; break;

			/* 18.8.26 i CT_BooleanProperty */
			case '<i': font.italic = y.val ? parsexmlbool(y.val) : 1; break;
			case '<i/>': font.italic = 1; break;

			/* 18.4.13 u CT_UnderlineProperty */
			case '<u':
				switch(y.val) {
					case "none": font.underline = 0x00; break;
					case "single": font.underline = 0x01; break;
					case "double": font.underline = 0x02; break;
					case "singleAccounting": font.underline = 0x21; break;
					case "doubleAccounting": font.underline = 0x22; break;
				} break;
			case '<u/>': font.underline = 1; break;

			/* 18.4.10 strike CT_BooleanProperty */
			case '<strike': font.strike = y.val ? parsexmlbool(y.val) : 1; break;
			case '<strike/>': font.strike = 1; break;

			/* 18.4.2  outline CT_BooleanProperty */
			case '<outline': font.outline = y.val ? parsexmlbool(y.val) : 1; break;
			case '<outline/>': font.outline = 1; break;

			/* 18.8.36 shadow CT_BooleanProperty */
			case '<shadow': font.shadow = y.val ? parsexmlbool(y.val) : 1; break;
			case '<shadow/>': font.shadow = 1; break;

			/* 18.8.12 condense CT_BooleanProperty */
			case '<condense': font.condense = y.val ? parsexmlbool(y.val) : 1; break;
			case '<condense/>': font.condense = 1; break;

			/* 18.8.17 extend CT_BooleanProperty */
			case '<extend': font.extend = y.val ? parsexmlbool(y.val) : 1; break;
			case '<extend/>': font.extend = 1; break;

			/* 18.4.11 sz CT_FontSize */
			case '<sz': if(y.val) font.sz = +y.val; break;
			case '<sz/>': case '</sz>': break;

			/* 18.4.14 vertAlign CT_VerticalAlignFontProperty */
			case '<vertAlign': if(y.val) font.vertAlign = y.val; break;
			case '<vertAlign/>': case '</vertAlign>': break;

			/* 18.8.18 family CT_FontFamily */
			case '<family': if(y.val) font.family = parseInt(y.val,10); break;
			case '<family/>': case '</family>': break;

			/* 18.8.35 scheme CT_FontScheme */
			case '<scheme': if(y.val) font.scheme = y.val; break;
			case '<scheme/>': case '</scheme>': break;

			/* 18.4.1 charset CT_IntProperty */
			case '<charset':
				if(y.val == '1') break;
				y.codepage = CS2CP[parseInt(y.val, 10)];
				break;

			/* 18.?.? color CT_Color */
			case '<color':
				if(!font.color) font.color = {};
				if(y.auto) font.color.auto = parsexmlbool(y.auto);

				if(y.rgb) font.color.rgb = y.rgb;
				else if(y.indexed) {
					font.color.index = parseInt(y.indexed, 10);
					var icv = XLSIcv[font.color.index];
					if(font.color.index == 81) icv = XLSIcv[1];
					if(!icv) throw new Error(x);
					font.color.rgb = icv[0].toString(16) + icv[1].toString(16) + icv[2].toString(16);
				} else if(y.theme) {
					font.color.theme = parseInt(y.theme, 10);
					if(y.tint) font.color.tint = parseFloat(y.tint);
					if(y.theme && themes.themeElements && themes.themeElements.clrScheme) {
						font.color.rgb = rgb_tint(themes.themeElements.clrScheme[font.color.theme].rgb, font.color.tint || 0);
					}
				}

				break;
			case '<color/>': case '</color>': break;

			default: if(opts && opts.WTF) throw new Error('unrecognized ' + y[0] + ' in fonts');
		}
	});
}

/* 18.8.31 numFmts CT_NumFmts */
function parse_numFmts(t, styles, opts) {
	styles.NumberFmt = [];
	var k/*Array<number>*/ = (keys(SSF._table));
	for(var i=0; i < k.length; ++i) styles.NumberFmt[k[i]] = SSF._table[k[i]];
	var m = t[0].match(tagregex);
	if(!m) return;
	for(i=0; i < m.length; ++i) {
		var y = parsexmltag(m[i]);
		switch(y[0]) {
			case '<numFmts': case '</numFmts>': case '<numFmts/>': case '<numFmts>': break;
			case '<numFmt': {
				var f=unescapexml(utf8read(y.formatCode)), j=parseInt(y.numFmtId,10);
				styles.NumberFmt[j] = f; if(j>0) SSF.load(f,j);
			} break;
			case '</numFmt>': break;
			default: if(opts.WTF) throw new Error('unrecognized ' + y[0] + ' in numFmts');
		}
	}
}

function write_numFmts(NF, opts) {
	var o = ["<numFmts>"];
	[[5,8],[23,26],[41,44],[/*63*/50,/*66],[164,*/392]].forEach(function(r) {
		for(var i = r[0]; i <= r[1]; ++i) if(NF[i] != null) o[o.length] = (writextag('numFmt',null,{numFmtId:i,formatCode:escapexml(NF[i])}));
	});
	if(o.length === 1) return "";
	o[o.length] = ("</numFmts>");
	o[0] = writextag('numFmts', null, { count:o.length-2 }).replace("/>", ">");
	return o.join("");
}

/* 18.8.10 cellXfs CT_CellXfs */
function parse_cellXfs(t, styles, opts) {
	styles.CellXf = [];
	var xf;
	t[0].match(tagregex).forEach(function(x) {
		var y = parsexmltag(x);
		switch(y[0]) {
			case '<cellXfs': case '<cellXfs>': case '<cellXfs/>': case '</cellXfs>': break;

			/* 18.8.45 xf CT_Xf */
			case '<xf':
				xf = y;
				delete xf[0];
				if(xf.numFmtId) xf.numFmtId = parseInt(xf.numFmtId, 10);
				if(xf.fillId) xf.fillId = parseInt(xf.fillId, 10);
				styles.CellXf.push(xf); break;
			case '</xf>': break;

			/* 18.8.1 alignment CT_CellAlignment */
			case '<alignment': case '<alignment/>':
				var alignment = {};
				if(y.vertical) alignment.vertical = y.vertical;
				if(y.horizontal) alignment.horizontal = y.horizontal;
				if(y.textRotation != null) alignment.textRotation = y.textRotation;
				if(y.indent) alignment.indent = y.indent;
				if(y.wrapText) alignment.wrapText = y.wrapText;
				xf.alignment = alignment;
				break;
			case '</alignment>': break;

			/* 18.8.33 protection CT_CellProtection */
			case '<protection': case '</protection>': case '<protection/>': break;

			/* 18.2.10 extLst CT_ExtensionList ? */
			case '<extLst': case '</extLst>': break;
			case '<ext': break;
			default: if(opts.WTF) throw new Error('unrecognized ' + y[0] + ' in cellXfs');
		}
	});
}

function write_cellXfs(cellXfs) {
	var o = [];
	o[o.length] = (writextag('cellXfs',null));
	cellXfs.forEach(function(c) { o[o.length] = (writextag('xf', null, c)); });
	o[o.length] = ("</cellXfs>");
	if(o.length === 2) return "";
	o[0] = writextag('cellXfs',null, {count:o.length-2}).replace("/>",">");
	return o.join("");
}

/* 18.8 Styles CT_Stylesheet*/
var parse_sty_xml= (function make_pstyx() {
var numFmtRegex = /<numFmts([^>]*)>.*<\/numFmts>/;
var cellXfRegex = /<cellXfs([^>]*)>.*<\/cellXfs>/;
var fillsRegex = /<fills([^>]*)>.*<\/fills>/;
var fontsRegex = /<fonts([^>]*)>.*<\/fonts>/;
var bordersRegex = /<borders([^>]*)>.*<\/borders>/;

return function parse_sty_xml(data, themes, opts) {
	var styles = {};
	if(!data) return styles;
	/* 18.8.39 styleSheet CT_Stylesheet */
	var t;

	/* 18.8.31 numFmts CT_NumFmts ? */
	if((t=data.match(numFmtRegex))) parse_numFmts(t, styles, opts);

	/* 18.8.23 fonts CT_Fonts ? */
	if((t=data.match(fontsRegex))) parse_fonts(t, styles, themes, opts);

	/* 18.8.21 fills CT_Fills ? */
	if((t=data.match(fillsRegex))) parse_fills(t, styles, themes, opts);

	/* 18.8.5  borders CT_Borders ? */
	if((t=data.match(bordersRegex))) parse_borders(t, styles, themes, opts);

	/* 18.8.9  cellStyleXfs CT_CellStyleXfs ? */

	/* 18.8.10 cellXfs CT_CellXfs ? */
	if((t=data.match(cellXfRegex))) parse_cellXfs(t, styles, opts);

	/* 18.8.8  cellStyles CT_CellStyles ? */
	/* 18.8.15 dxfs CT_Dxfs ? */
	/* 18.8.42 tableStyles CT_TableStyles ? */
	/* 18.8.11 colors CT_Colors ? */
	/* 18.2.10 extLst CT_ExtensionList ? */

	return styles;
};
})();

var STYLES_XML_ROOT = writextag('styleSheet', null, {
	'xmlns': XMLNS.main[0],
	'xmlns:vt': XMLNS.vt
});

RELS.STY = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles";

function write_sty_xml(wb, opts) {
	var o = [XML_HEADER, STYLES_XML_ROOT], w;
	if(wb.SSF && (w = write_numFmts(wb.SSF)) != null) o[o.length] = w;
	o[o.length] = ('<fonts count="1"><font><sz val="12"/><color theme="1"/><name val="Calibri"/><family val="2"/><scheme val="minor"/></font></fonts>');
	o[o.length] = ('<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>');
	o[o.length] = ('<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>');
	o[o.length] = ('<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>');
	if((w = write_cellXfs(opts.cellXfs))) o[o.length] = (w);
	o[o.length] = ('<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>');
	o[o.length] = ('<dxfs count="0"/>');
	o[o.length] = ('<tableStyles count="0" defaultTableStyle="TableStyleMedium9" defaultPivotStyle="PivotStyleMedium4"/>');

	if(o.length>2){ o[o.length] = ('</styleSheet>'); o[1]=o[1].replace("/>",">"); }
	return o.join("");
}
/* [MS-XLSB] 2.4.651 BrtFmt */
function parse_BrtFmt(data, length) {
	var ifmt = data.read_shift(2);
	var stFmtCode = parse_XLWideString(data,length-2);
	return [ifmt, stFmtCode];
}
function write_BrtFmt(i, f, o) {
	if(!o) o = new_buf(6 + 4 * f.length);
	o.write_shift(2, i);
	write_XLWideString(f, o);
	return o.length > o.l ? o.slice(0, o.l) : o;
}

/* [MS-XLSB] 2.4.653 BrtFont TODO */
function parse_BrtFont(data, length, opts) {
	var out = ({});

	out.sz = data.read_shift(2) / 20;

	var grbit = parse_FontFlags(data, 2, opts);
	if(grbit.fCondense) out.condense = 1;
	if(grbit.fExtend) out.extend = 1;
	if(grbit.fShadow) out.shadow = 1;
	if(grbit.fOutline) out.outline = 1;
	if(grbit.fStrikeout) out.strike = 1;
	if(grbit.fItalic) out.italic = 1;

	var bls = data.read_shift(2);
	if(bls === 0x02BC) out.bold = 1;

	switch(data.read_shift(2)) {
		/* case 0: out.vertAlign = "baseline"; break; */
		case 1: out.vertAlign = "superscript"; break;
		case 2: out.vertAlign = "subscript"; break;
	}

	var underline = data.read_shift(1);
	if(underline != 0) out.underline = underline;

	var family = data.read_shift(1);
	if(family > 0) out.family = family;

	var bCharSet = data.read_shift(1);
	if(bCharSet > 0) out.charset = bCharSet;

	data.l++;
	out.color = parse_BrtColor(data, 8);

	switch(data.read_shift(1)) {
		/* case 0: out.scheme = "none": break; */
		case 1: out.scheme = "major"; break;
		case 2: out.scheme = "minor"; break;
	}

	out.name = parse_XLWideString(data, length - 21);

	return out;
}
function write_BrtFont(font, o) {
	if(!o) o = new_buf(25+4*32);
	o.write_shift(2, font.sz * 20);
	write_FontFlags(font, o);
	o.write_shift(2, font.bold ? 0x02BC : 0x0190);
	var sss = 0;
	if(font.vertAlign == "superscript") sss = 1;
	else if(font.vertAlign == "subscript") sss = 2;
	o.write_shift(2, sss);
	o.write_shift(1, font.underline || 0);
	o.write_shift(1, font.family || 0);
	o.write_shift(1, font.charset || 0);
	o.write_shift(1, 0);
	write_BrtColor(font.color, o);
	var scheme = 0;
	if(font.scheme == "major") scheme = 1;
	if(font.scheme == "minor") scheme = 2;
	o.write_shift(1, scheme);
	write_XLWideString(font.name, o);
	return o.length > o.l ? o.slice(0, o.l) : o;
}

/* [MS-XLSB] 2.4.644 BrtFill */
var XLSBFillPTNames = [
	"none",
	"solid",
	"mediumGray",
	"darkGray",
	"lightGray",
	"darkHorizontal",
	"darkVertical",
	"darkDown",
	"darkUp",
	"darkGrid",
	"darkTrellis",
	"lightHorizontal",
	"lightVertical",
	"lightDown",
	"lightUp",
	"lightGrid",
	"lightTrellis",
	"gray125",
	"gray0625"
];
var rev_XLSBFillPTNames = (evert(XLSBFillPTNames));
/* TODO: gradient fill representation */
function write_BrtFill(fill, o) {
	if(!o) o = new_buf(4*3 + 8*7 + 16*1);
	var fls = rev_XLSBFillPTNames[fill.patternType];
	if(fls == null) fls = 0x28;
	o.write_shift(4, fls);
	var j = 0;
	if(fls != 0x28) {
		/* TODO: custom FG Color */
		write_BrtColor({auto:1}, o);
		/* TODO: custom BG Color */
		write_BrtColor({auto:1}, o);

		for(; j < 12; ++j) o.write_shift(4, 0);
	} else {
		for(; j < 4; ++j) o.write_shift(4, 0);

		for(; j < 12; ++j) o.write_shift(4, 0); /* TODO */
		/* iGradientType */
		/* xnumDegree */
		/* xnumFillToLeft */
		/* xnumFillToRight */
		/* xnumFillToTop */
		/* xnumFillToBottom */
		/* cNumStop */
		/* xfillGradientStop */
	}
	return o.length > o.l ? o.slice(0, o.l) : o;
}

/* [MS-XLSB] 2.4.816 BrtXF */
function parse_BrtXF(data, length) {
	var ixfeParent = data.read_shift(2);
	var ifmt = data.read_shift(2);
	parsenoop(data, length-4);
	return {ixfe:ixfeParent, ifmt:ifmt };
}
function write_BrtXF(data, ixfeP, o) {
	if(!o) o = new_buf(16);
	o.write_shift(2, ixfeP||0);
	o.write_shift(2, data.numFmtId||0);
	o.write_shift(2, 0); /* iFont */
	o.write_shift(2, 0); /* iFill */
	o.write_shift(2, 0); /* ixBorder */
	o.write_shift(1, 0); /* trot */
	o.write_shift(1, 0); /* indent */
	o.write_shift(1, 0); /* flags */
	o.write_shift(1, 0); /* flags */
	o.write_shift(1, 0); /* xfGrbitAtr */
	o.write_shift(1, 0);
	return o;
}

/* [MS-XLSB] 2.5.4 Blxf TODO */
function write_Blxf(data, o) {
	if(!o) o = new_buf(10);
	o.write_shift(1, 0); /* dg */
	o.write_shift(1, 0);
	o.write_shift(4, 0); /* color */
	o.write_shift(4, 0); /* color */
	return o;
}
/* [MS-XLSB] 2.4.299 BrtBorder TODO */
function write_BrtBorder(border, o) {
	if(!o) o = new_buf(51);
	o.write_shift(1, 0); /* diagonal */
	write_Blxf(null, o); /* top */
	write_Blxf(null, o); /* bottom */
	write_Blxf(null, o); /* left */
	write_Blxf(null, o); /* right */
	write_Blxf(null, o); /* diag */
	return o.length > o.l ? o.slice(0, o.l) : o;
}

/* [MS-XLSB] 2.4.755 BrtStyle TODO */
function write_BrtStyle(style, o) {
	if(!o) o = new_buf(12+4*10);
	o.write_shift(4, style.xfId);
	o.write_shift(2, 1);
	o.write_shift(1, +style.builtinId);
	o.write_shift(1, 0); /* iLevel */
	write_XLNullableWideString(style.name || "", o);
	return o.length > o.l ? o.slice(0, o.l) : o;
}

/* [MS-XLSB] 2.4.269 BrtBeginTableStyles */
function write_BrtBeginTableStyles(cnt, defTableStyle, defPivotStyle) {
	var o = new_buf(4+256*2*4);
	o.write_shift(4, cnt);
	write_XLNullableWideString(defTableStyle, o);
	write_XLNullableWideString(defPivotStyle, o);
	return o.length > o.l ? o.slice(0, o.l) : o;
}

/* [MS-XLSB] 2.1.7.50 Styles */
function parse_sty_bin(data, themes, opts) {
	var styles = {};
	styles.NumberFmt = ([]);
	for(var y in SSF._table) styles.NumberFmt[y] = SSF._table[y];

	styles.CellXf = [];
	styles.Fonts = [];
	var state = [];
	var pass = false;
	recordhopper(data, function hopper_sty(val, R_n, RT) {
		switch(RT) {
			case 0x002C: /* 'BrtFmt' */
				styles.NumberFmt[val[0]] = val[1]; SSF.load(val[1], val[0]);
				break;
			case 0x002B: /* 'BrtFont' */
				styles.Fonts.push(val);
				if(val.color.theme != null && themes && themes.themeElements && themes.themeElements.clrScheme) {
					val.color.rgb = rgb_tint(themes.themeElements.clrScheme[val.color.theme].rgb, val.color.tint || 0);
				}
				break;
			case 0x0401: /* 'BrtKnownFonts' */ break;
			case 0x002D: /* 'BrtFill' */ break;
			case 0x002E: /* 'BrtBorder' */ break;
			case 0x002F: /* 'BrtXF' */
				if(state[state.length - 1] == "BrtBeginCellXFs") {
					styles.CellXf.push(val);
				}
				break;
			case 0x0030: /* 'BrtStyle' */
			case 0x01FB: /* 'BrtDXF' */
			case 0x023C: /* 'BrtMRUColor' */
			case 0x01DB: /* 'BrtIndexedColor': */
				break;

			case 0x0493: /* 'BrtDXF14' */
			case 0x0836: /* 'BrtDXF15' */
			case 0x046A: /* 'BrtSlicerStyleElement' */
			case 0x0200: /* 'BrtTableStyleElement' */
			case 0x082F: /* 'BrtTimelineStyleElement' */
			/* case 'BrtUid' */
				break;

			case 0x0023: /* 'BrtFRTBegin' */
				pass = true; break;
			case 0x0024: /* 'BrtFRTEnd' */
				pass = false; break;
			case 0x0025: /* 'BrtACBegin' */
				state.push(R_n); break;
			case 0x0026: /* 'BrtACEnd' */
				state.pop(); break;

			default:
				if((R_n||"").indexOf("Begin") > 0) state.push(R_n);
				else if((R_n||"").indexOf("End") > 0) state.pop();
				else if(!pass || opts.WTF) throw new Error("Unexpected record " + RT + " " + R_n);
		}
	});
	return styles;
}

function write_FMTS_bin(ba, NF) {
	if(!NF) return;
	var cnt = 0;
	[[5,8],[23,26],[41,44],[/*63*/57,/*66],[164,*/392]].forEach(function(r) {
for(var i = r[0]; i <= r[1]; ++i) if(NF[i] != null) ++cnt;
	});

	if(cnt == 0) return;
	write_record(ba, "BrtBeginFmts", write_UInt32LE(cnt));
	[[5,8],[23,26],[41,44],[/*63*/57,/*66],[164,*/392]].forEach(function(r) {
for(var i = r[0]; i <= r[1]; ++i) if(NF[i] != null) write_record(ba, "BrtFmt", write_BrtFmt(i, NF[i]));
	});
	write_record(ba, "BrtEndFmts");
}

function write_FONTS_bin(ba, data) {
	var cnt = 1;

	if(cnt == 0) return;
	write_record(ba, "BrtBeginFonts", write_UInt32LE(cnt));
	write_record(ba, "BrtFont", write_BrtFont({
		sz:12,
		color: {theme:1},
		name: "Calibri",
		family: 2,
		scheme: "minor"
	}));
	/* 1*65491BrtFont [ACFONTS] */
	write_record(ba, "BrtEndFonts");
}

function write_FILLS_bin(ba, data) {
	var cnt = 2;

	if(cnt == 0) return;
	write_record(ba, "BrtBeginFills", write_UInt32LE(cnt));
	write_record(ba, "BrtFill", write_BrtFill({patternType:"none"}));
	write_record(ba, "BrtFill", write_BrtFill({patternType:"gray125"}));
	/* 1*65431BrtFill */
	write_record(ba, "BrtEndFills");
}

function write_BORDERS_bin(ba, data) {
	var cnt = 1;

	if(cnt == 0) return;
	write_record(ba, "BrtBeginBorders", write_UInt32LE(cnt));
	write_record(ba, "BrtBorder", write_BrtBorder({}));
	/* 1*65430BrtBorder */
	write_record(ba, "BrtEndBorders");
}

function write_CELLSTYLEXFS_bin(ba, data) {
	var cnt = 1;
	write_record(ba, "BrtBeginCellStyleXFs", write_UInt32LE(cnt));
	write_record(ba, "BrtXF", write_BrtXF({
		numFmtId:0,
		fontId:0,
		fillId:0,
		borderId:0
	}, 0xFFFF));
	/* 1*65430(BrtXF *FRT) */
	write_record(ba, "BrtEndCellStyleXFs");
}

function write_CELLXFS_bin(ba, data) {
	write_record(ba, "BrtBeginCellXFs", write_UInt32LE(data.length));
	data.forEach(function(c) { write_record(ba, "BrtXF", write_BrtXF(c,0)); });
	/* 1*65430(BrtXF *FRT) */
	write_record(ba, "BrtEndCellXFs");
}

function write_STYLES_bin(ba, data) {
	var cnt = 1;

	write_record(ba, "BrtBeginStyles", write_UInt32LE(1));
	write_record(ba, "BrtStyle", write_BrtStyle({
		xfId:0,
		builtinId:0,
		name:"Normal"
	}));
	/* 1*65430(BrtStyle *FRT) */
	write_record(ba, "BrtEndStyles");
}

function write_DXFS_bin(ba, data) {
	var cnt = 0;

	write_record(ba, "BrtBeginDXFs", write_UInt32LE(cnt));
	/* *2147483647(BrtDXF *FRT) */
	write_record(ba, "BrtEndDXFs");
}

function write_TABLESTYLES_bin(ba, data) {
	var cnt = 0;

	write_record(ba, "BrtBeginTableStyles", write_BrtBeginTableStyles(cnt, "TableStyleMedium9", "PivotStyleMedium4"));
	/* *TABLESTYLE */
	write_record(ba, "BrtEndTableStyles");
}

function write_COLORPALETTE_bin(ba, data) {
	return;
	/* BrtBeginColorPalette [INDEXEDCOLORS] [MRUCOLORS] BrtEndColorPalette */
}

/* [MS-XLSB] 2.1.7.50 Styles */
function write_sty_bin(wb, opts) {
	var ba = buf_array();
	write_record(ba, "BrtBeginStyleSheet");
	write_FMTS_bin(ba, wb.SSF);
	write_FONTS_bin(ba, wb);
	write_FILLS_bin(ba, wb);
	write_BORDERS_bin(ba, wb);
	write_CELLSTYLEXFS_bin(ba, wb);
	write_CELLXFS_bin(ba, opts.cellXfs);
	write_STYLES_bin(ba, wb);
	write_DXFS_bin(ba, wb);
	write_TABLESTYLES_bin(ba, wb);
	write_COLORPALETTE_bin(ba, wb);
	/* FRTSTYLESHEET*/
	write_record(ba, "BrtEndStyleSheet");
	return ba.end();
}
RELS.THEME = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme";

/* 20.1.6.2 clrScheme CT_ColorScheme */
function parse_clrScheme(t, themes, opts) {
	themes.themeElements.clrScheme = [];
	var color = {};
	(t[0].match(tagregex)||[]).forEach(function(x) {
		var y = parsexmltag(x);
		switch(y[0]) {
			/* 20.1.6.2 clrScheme (Color Scheme) CT_ColorScheme */
			case '<a:clrScheme': case '</a:clrScheme>': break;

			/* 20.1.2.3.32 srgbClr CT_SRgbColor */
			case '<a:srgbClr':
				color.rgb = y.val; break;

			/* 20.1.2.3.33 sysClr CT_SystemColor */
			case '<a:sysClr':
				color.rgb = y.lastClr; break;

			/* 20.1.4.1.1 accent1 (Accent 1) */
			/* 20.1.4.1.2 accent2 (Accent 2) */
			/* 20.1.4.1.3 accent3 (Accent 3) */
			/* 20.1.4.1.4 accent4 (Accent 4) */
			/* 20.1.4.1.5 accent5 (Accent 5) */
			/* 20.1.4.1.6 accent6 (Accent 6) */
			/* 20.1.4.1.9 dk1 (Dark 1) */
			/* 20.1.4.1.10 dk2 (Dark 2) */
			/* 20.1.4.1.15 folHlink (Followed Hyperlink) */
			/* 20.1.4.1.19 hlink (Hyperlink) */
			/* 20.1.4.1.22 lt1 (Light 1) */
			/* 20.1.4.1.23 lt2 (Light 2) */
			case '<a:dk1>': case '</a:dk1>':
			case '<a:lt1>': case '</a:lt1>':
			case '<a:dk2>': case '</a:dk2>':
			case '<a:lt2>': case '</a:lt2>':
			case '<a:accent1>': case '</a:accent1>':
			case '<a:accent2>': case '</a:accent2>':
			case '<a:accent3>': case '</a:accent3>':
			case '<a:accent4>': case '</a:accent4>':
			case '<a:accent5>': case '</a:accent5>':
			case '<a:accent6>': case '</a:accent6>':
			case '<a:hlink>': case '</a:hlink>':
			case '<a:folHlink>': case '</a:folHlink>':
				if (y[0][1] === '/') {
					themes.themeElements.clrScheme.push(color);
					color = {};
				} else {
					color.name = y[0].substring(3, y[0].length - 1);
				}
				break;

			default: if(opts && opts.WTF) throw new Error('Unrecognized ' + y[0] + ' in clrScheme');
		}
	});
}

/* 20.1.4.1.18 fontScheme CT_FontScheme */
function parse_fontScheme(t, themes, opts) { }

/* 20.1.4.1.15 fmtScheme CT_StyleMatrix */
function parse_fmtScheme(t, themes, opts) { }

var clrsregex = /<a:clrScheme([^>]*)>[^\u2603]*<\/a:clrScheme>/;
var fntsregex = /<a:fontScheme([^>]*)>[^\u2603]*<\/a:fontScheme>/;
var fmtsregex = /<a:fmtScheme([^>]*)>[^\u2603]*<\/a:fmtScheme>/;

/* 20.1.6.10 themeElements CT_BaseStyles */
function parse_themeElements(data, themes, opts) {
	themes.themeElements = {};

	var t;

	[
		/* clrScheme CT_ColorScheme */
		['clrScheme', clrsregex, parse_clrScheme],
		/* fontScheme CT_FontScheme */
		['fontScheme', fntsregex, parse_fontScheme],
		/* fmtScheme CT_StyleMatrix */
		['fmtScheme', fmtsregex, parse_fmtScheme]
	].forEach(function(m) {
		if(!(t=data.match(m[1]))) throw new Error(m[0] + ' not found in themeElements');
		m[2](t, themes, opts);
	});
}

var themeltregex = /<a:themeElements([^>]*)>[^\u2603]*<\/a:themeElements>/;

/* 14.2.7 Theme Part */
function parse_theme_xml(data, opts) {
	/* 20.1.6.9 theme CT_OfficeStyleSheet */
	if(!data || data.length === 0) return parse_theme_xml(write_theme());

	var t;
	var themes = {};

	/* themeElements CT_BaseStyles */
	if(!(t=data.match(themeltregex))) throw new Error('themeElements not found in theme');
	parse_themeElements(t[0], themes, opts);

	return themes;
}

function write_theme(Themes, opts) {
	if(opts && opts.themeXLSX) return opts.themeXLSX;
	var o = [XML_HEADER];
	o[o.length] = '<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Office Theme">';
	o[o.length] =  '<a:themeElements>';

	o[o.length] =   '<a:clrScheme name="Office">';
	o[o.length] =    '<a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1>';
	o[o.length] =    '<a:lt1><a:sysClr val="window" lastClr="FFFFFF"/></a:lt1>';
	o[o.length] =    '<a:dk2><a:srgbClr val="1F497D"/></a:dk2>';
	o[o.length] =    '<a:lt2><a:srgbClr val="EEECE1"/></a:lt2>';
	o[o.length] =    '<a:accent1><a:srgbClr val="4F81BD"/></a:accent1>';
	o[o.length] =    '<a:accent2><a:srgbClr val="C0504D"/></a:accent2>';
	o[o.length] =    '<a:accent3><a:srgbClr val="9BBB59"/></a:accent3>';
	o[o.length] =    '<a:accent4><a:srgbClr val="8064A2"/></a:accent4>';
	o[o.length] =    '<a:accent5><a:srgbClr val="4BACC6"/></a:accent5>';
	o[o.length] =    '<a:accent6><a:srgbClr val="F79646"/></a:accent6>';
	o[o.length] =    '<a:hlink><a:srgbClr val="0000FF"/></a:hlink>';
	o[o.length] =    '<a:folHlink><a:srgbClr val="800080"/></a:folHlink>';
	o[o.length] =   '</a:clrScheme>';

	o[o.length] =   '<a:fontScheme name="Office">';
	o[o.length] =    '<a:majorFont>';
	o[o.length] =     '<a:latin typeface="Cambria"/>';
	o[o.length] =     '<a:ea typeface=""/>';
	o[o.length] =     '<a:cs typeface=""/>';
	o[o.length] =     '<a:font script="Jpan" typeface="ＭＳ Ｐゴシック"/>';
	o[o.length] =     '<a:font script="Hang" typeface="맑은 고딕"/>';
	o[o.length] =     '<a:font script="Hans" typeface="宋体"/>';
	o[o.length] =     '<a:font script="Hant" typeface="新細明體"/>';
	o[o.length] =     '<a:font script="Arab" typeface="Times New Roman"/>';
	o[o.length] =     '<a:font script="Hebr" typeface="Times New Roman"/>';
	o[o.length] =     '<a:font script="Thai" typeface="Tahoma"/>';
	o[o.length] =     '<a:font script="Ethi" typeface="Nyala"/>';
	o[o.length] =     '<a:font script="Beng" typeface="Vrinda"/>';
	o[o.length] =     '<a:font script="Gujr" typeface="Shruti"/>';
	o[o.length] =     '<a:font script="Khmr" typeface="MoolBoran"/>';
	o[o.length] =     '<a:font script="Knda" typeface="Tunga"/>';
	o[o.length] =     '<a:font script="Guru" typeface="Raavi"/>';
	o[o.length] =     '<a:font script="Cans" typeface="Euphemia"/>';
	o[o.length] =     '<a:font script="Cher" typeface="Plantagenet Cherokee"/>';
	o[o.length] =     '<a:font script="Yiii" typeface="Microsoft Yi Baiti"/>';
	o[o.length] =     '<a:font script="Tibt" typeface="Microsoft Himalaya"/>';
	o[o.length] =     '<a:font script="Thaa" typeface="MV Boli"/>';
	o[o.length] =     '<a:font script="Deva" typeface="Mangal"/>';
	o[o.length] =     '<a:font script="Telu" typeface="Gautami"/>';
	o[o.length] =     '<a:font script="Taml" typeface="Latha"/>';
	o[o.length] =     '<a:font script="Syrc" typeface="Estrangelo Edessa"/>';
	o[o.length] =     '<a:font script="Orya" typeface="Kalinga"/>';
	o[o.length] =     '<a:font script="Mlym" typeface="Kartika"/>';
	o[o.length] =     '<a:font script="Laoo" typeface="DokChampa"/>';
	o[o.length] =     '<a:font script="Sinh" typeface="Iskoola Pota"/>';
	o[o.length] =     '<a:font script="Mong" typeface="Mongolian Baiti"/>';
	o[o.length] =     '<a:font script="Viet" typeface="Times New Roman"/>';
	o[o.length] =     '<a:font script="Uigh" typeface="Microsoft Uighur"/>';
	o[o.length] =     '<a:font script="Geor" typeface="Sylfaen"/>';
	o[o.length] =    '</a:majorFont>';
	o[o.length] =    '<a:minorFont>';
	o[o.length] =     '<a:latin typeface="Calibri"/>';
	o[o.length] =     '<a:ea typeface=""/>';
	o[o.length] =     '<a:cs typeface=""/>';
	o[o.length] =     '<a:font script="Jpan" typeface="ＭＳ Ｐゴシック"/>';
	o[o.length] =     '<a:font script="Hang" typeface="맑은 고딕"/>';
	o[o.length] =     '<a:font script="Hans" typeface="宋体"/>';
	o[o.length] =     '<a:font script="Hant" typeface="新細明體"/>';
	o[o.length] =     '<a:font script="Arab" typeface="Arial"/>';
	o[o.length] =     '<a:font script="Hebr" typeface="Arial"/>';
	o[o.length] =     '<a:font script="Thai" typeface="Tahoma"/>';
	o[o.length] =     '<a:font script="Ethi" typeface="Nyala"/>';
	o[o.length] =     '<a:font script="Beng" typeface="Vrinda"/>';
	o[o.length] =     '<a:font script="Gujr" typeface="Shruti"/>';
	o[o.length] =     '<a:font script="Khmr" typeface="DaunPenh"/>';
	o[o.length] =     '<a:font script="Knda" typeface="Tunga"/>';
	o[o.length] =     '<a:font script="Guru" typeface="Raavi"/>';
	o[o.length] =     '<a:font script="Cans" typeface="Euphemia"/>';
	o[o.length] =     '<a:font script="Cher" typeface="Plantagenet Cherokee"/>';
	o[o.length] =     '<a:font script="Yiii" typeface="Microsoft Yi Baiti"/>';
	o[o.length] =     '<a:font script="Tibt" typeface="Microsoft Himalaya"/>';
	o[o.length] =     '<a:font script="Thaa" typeface="MV Boli"/>';
	o[o.length] =     '<a:font script="Deva" typeface="Mangal"/>';
	o[o.length] =     '<a:font script="Telu" typeface="Gautami"/>';
	o[o.length] =     '<a:font script="Taml" typeface="Latha"/>';
	o[o.length] =     '<a:font script="Syrc" typeface="Estrangelo Edessa"/>';
	o[o.length] =     '<a:font script="Orya" typeface="Kalinga"/>';
	o[o.length] =     '<a:font script="Mlym" typeface="Kartika"/>';
	o[o.length] =     '<a:font script="Laoo" typeface="DokChampa"/>';
	o[o.length] =     '<a:font script="Sinh" typeface="Iskoola Pota"/>';
	o[o.length] =     '<a:font script="Mong" typeface="Mongolian Baiti"/>';
	o[o.length] =     '<a:font script="Viet" typeface="Arial"/>';
	o[o.length] =     '<a:font script="Uigh" typeface="Microsoft Uighur"/>';
	o[o.length] =     '<a:font script="Geor" typeface="Sylfaen"/>';
	o[o.length] =    '</a:minorFont>';
	o[o.length] =   '</a:fontScheme>';

	o[o.length] =   '<a:fmtScheme name="Office">';
	o[o.length] =    '<a:fillStyleLst>';
	o[o.length] =     '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>';
	o[o.length] =     '<a:gradFill rotWithShape="1">';
	o[o.length] =      '<a:gsLst>';
	o[o.length] =       '<a:gs pos="0"><a:schemeClr val="phClr"><a:tint val="50000"/><a:satMod val="300000"/></a:schemeClr></a:gs>';
	o[o.length] =       '<a:gs pos="35000"><a:schemeClr val="phClr"><a:tint val="37000"/><a:satMod val="300000"/></a:schemeClr></a:gs>';
	o[o.length] =       '<a:gs pos="100000"><a:schemeClr val="phClr"><a:tint val="15000"/><a:satMod val="350000"/></a:schemeClr></a:gs>';
	o[o.length] =      '</a:gsLst>';
	o[o.length] =      '<a:lin ang="16200000" scaled="1"/>';
	o[o.length] =     '</a:gradFill>';
	o[o.length] =     '<a:gradFill rotWithShape="1">';
	o[o.length] =      '<a:gsLst>';
	o[o.length] =       '<a:gs pos="0"><a:schemeClr val="phClr"><a:tint val="100000"/><a:shade val="100000"/><a:satMod val="130000"/></a:schemeClr></a:gs>';
	o[o.length] =       '<a:gs pos="100000"><a:schemeClr val="phClr"><a:tint val="50000"/><a:shade val="100000"/><a:satMod val="350000"/></a:schemeClr></a:gs>';
	o[o.length] =      '</a:gsLst>';
	o[o.length] =      '<a:lin ang="16200000" scaled="0"/>';
	o[o.length] =     '</a:gradFill>';
	o[o.length] =    '</a:fillStyleLst>';
	o[o.length] =    '<a:lnStyleLst>';
	o[o.length] =     '<a:ln w="9525" cap="flat" cmpd="sng" algn="ctr"><a:solidFill><a:schemeClr val="phClr"><a:shade val="95000"/><a:satMod val="105000"/></a:schemeClr></a:solidFill><a:prstDash val="solid"/></a:ln>';
	o[o.length] =     '<a:ln w="25400" cap="flat" cmpd="sng" algn="ctr"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:prstDash val="solid"/></a:ln>';
	o[o.length] =     '<a:ln w="38100" cap="flat" cmpd="sng" algn="ctr"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:prstDash val="solid"/></a:ln>';
	o[o.length] =    '</a:lnStyleLst>';
	o[o.length] =    '<a:effectStyleLst>';
	o[o.length] =     '<a:effectStyle>';
	o[o.length] =      '<a:effectLst>';
	o[o.length] =       '<a:outerShdw blurRad="40000" dist="20000" dir="5400000" rotWithShape="0"><a:srgbClr val="000000"><a:alpha val="38000"/></a:srgbClr></a:outerShdw>';
	o[o.length] =      '</a:effectLst>';
	o[o.length] =     '</a:effectStyle>';
	o[o.length] =     '<a:effectStyle>';
	o[o.length] =      '<a:effectLst>';
	o[o.length] =       '<a:outerShdw blurRad="40000" dist="23000" dir="5400000" rotWithShape="0"><a:srgbClr val="000000"><a:alpha val="35000"/></a:srgbClr></a:outerShdw>';
	o[o.length] =      '</a:effectLst>';
	o[o.length] =     '</a:effectStyle>';
	o[o.length] =     '<a:effectStyle>';
	o[o.length] =      '<a:effectLst>';
	o[o.length] =       '<a:outerShdw blurRad="40000" dist="23000" dir="5400000" rotWithShape="0"><a:srgbClr val="000000"><a:alpha val="35000"/></a:srgbClr></a:outerShdw>';
	o[o.length] =      '</a:effectLst>';
	o[o.length] =      '<a:scene3d><a:camera prst="orthographicFront"><a:rot lat="0" lon="0" rev="0"/></a:camera><a:lightRig rig="threePt" dir="t"><a:rot lat="0" lon="0" rev="1200000"/></a:lightRig></a:scene3d>';
	o[o.length] =      '<a:sp3d><a:bevelT w="63500" h="25400"/></a:sp3d>';
	o[o.length] =     '</a:effectStyle>';
	o[o.length] =    '</a:effectStyleLst>';
	o[o.length] =    '<a:bgFillStyleLst>';
	o[o.length] =     '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>';
	o[o.length] =     '<a:gradFill rotWithShape="1">';
	o[o.length] =      '<a:gsLst>';
	o[o.length] =       '<a:gs pos="0"><a:schemeClr val="phClr"><a:tint val="40000"/><a:satMod val="350000"/></a:schemeClr></a:gs>';
	o[o.length] =       '<a:gs pos="40000"><a:schemeClr val="phClr"><a:tint val="45000"/><a:shade val="99000"/><a:satMod val="350000"/></a:schemeClr></a:gs>';
	o[o.length] =       '<a:gs pos="100000"><a:schemeClr val="phClr"><a:shade val="20000"/><a:satMod val="255000"/></a:schemeClr></a:gs>';
	o[o.length] =      '</a:gsLst>';
	o[o.length] =      '<a:path path="circle"><a:fillToRect l="50000" t="-80000" r="50000" b="180000"/></a:path>';
	o[o.length] =     '</a:gradFill>';
	o[o.length] =     '<a:gradFill rotWithShape="1">';
	o[o.length] =      '<a:gsLst>';
	o[o.length] =       '<a:gs pos="0"><a:schemeClr val="phClr"><a:tint val="80000"/><a:satMod val="300000"/></a:schemeClr></a:gs>';
	o[o.length] =       '<a:gs pos="100000"><a:schemeClr val="phClr"><a:shade val="30000"/><a:satMod val="200000"/></a:schemeClr></a:gs>';
	o[o.length] =      '</a:gsLst>';
	o[o.length] =      '<a:path path="circle"><a:fillToRect l="50000" t="50000" r="50000" b="50000"/></a:path>';
	o[o.length] =     '</a:gradFill>';
	o[o.length] =    '</a:bgFillStyleLst>';
	o[o.length] =   '</a:fmtScheme>';
	o[o.length] =  '</a:themeElements>';

	o[o.length] =  '<a:objectDefaults>';
	o[o.length] =   '<a:spDef>';
	o[o.length] =    '<a:spPr/><a:bodyPr/><a:lstStyle/><a:style><a:lnRef idx="1"><a:schemeClr val="accent1"/></a:lnRef><a:fillRef idx="3"><a:schemeClr val="accent1"/></a:fillRef><a:effectRef idx="2"><a:schemeClr val="accent1"/></a:effectRef><a:fontRef idx="minor"><a:schemeClr val="lt1"/></a:fontRef></a:style>';
	o[o.length] =   '</a:spDef>';
	o[o.length] =   '<a:lnDef>';
	o[o.length] =    '<a:spPr/><a:bodyPr/><a:lstStyle/><a:style><a:lnRef idx="2"><a:schemeClr val="accent1"/></a:lnRef><a:fillRef idx="0"><a:schemeClr val="accent1"/></a:fillRef><a:effectRef idx="1"><a:schemeClr val="accent1"/></a:effectRef><a:fontRef idx="minor"><a:schemeClr val="tx1"/></a:fontRef></a:style>';
	o[o.length] =   '</a:lnDef>';
	o[o.length] =  '</a:objectDefaults>';
	o[o.length] =  '<a:extraClrSchemeLst/>';
	o[o.length] = '</a:theme>';
	return o.join("");
}
/* [MS-XLS] 2.4.326 TODO: payload is a zip file */
function parse_Theme(blob, length, opts) {
	var dwThemeVersion = blob.read_shift(4);
	if(dwThemeVersion === 124226) return;
	blob.l += length-4;
}

/* 2.5.49 */
function parse_ColorTheme(blob, length) { return blob.read_shift(4); }

/* 2.5.155 */
function parse_FullColorExt(blob, length) {
	var o = {};
	o.xclrType = blob.read_shift(2);
	o.nTintShade = blob.read_shift(2);
	switch(o.xclrType) {
		case 0: blob.l += 4; break;
		case 1: o.xclrValue = parse_IcvXF(blob, 4); break;
		case 2: o.xclrValue = parse_LongRGBA(blob, 4); break;
		case 3: o.xclrValue = parse_ColorTheme(blob, 4); break;
		case 4: blob.l += 4; break;
	}
	blob.l += 8;
	return o;
}

/* 2.5.164 TODO: read 7 bits*/
function parse_IcvXF(blob, length) {
	return parsenoop(blob, length);
}

/* 2.5.280 */
function parse_XFExtGradient(blob, length) {
	return parsenoop(blob, length);
}

/* 2.5.108 */
function parse_ExtProp(blob, length) {
	var extType = blob.read_shift(2);
	var cb = blob.read_shift(2);
	var o = [extType];
	switch(extType) {
		case 0x04: case 0x05: case 0x07: case 0x08:
		case 0x09: case 0x0A: case 0x0B: case 0x0D:
			o[1] = parse_FullColorExt(blob, cb); break;
		case 0x06: o[1] = parse_XFExtGradient(blob, cb); break;
		case 0x0E: case 0x0F: o[1] = blob.read_shift(cb === 5 ? 1 : 2); break;
		default: throw new Error("Unrecognized ExtProp type: " + extType + " " + cb);
	}
	return o;
}

/* 2.4.355 */
function parse_XFExt(blob, length) {
	var end = blob.l + length;
	blob.l += 2;
	var ixfe = blob.read_shift(2);
	blob.l += 2;
	var cexts = blob.read_shift(2);
	var ext = [];
	while(cexts-- > 0) ext.push(parse_ExtProp(blob, end-blob.l));
	return {ixfe:ixfe, ext:ext};
}

/* xf is an XF, see parse_XFExt for xfext */
function update_xfext(xf, xfext) {
	xfext.forEach(function(xfe) {
		switch(xfe[0]) { /* 2.5.108 extPropData */
			case 0x04: break; /* foreground color */
			case 0x05: break; /* background color */
			case 0x06: break; /* gradient fill */
			case 0x07: break; /* top cell border color */
			case 0x08: break; /* bottom cell border color */
			case 0x09: break; /* left cell border color */
			case 0x0a: break; /* right cell border color */
			case 0x0b: break; /* diagonal cell border color */
			case 0x0d: break; /* text color */
			case 0x0e: break; /* font scheme */
			case 0x0f: break; /* indentation level */
		}
	});
}

/* 18.6 Calculation Chain */
function parse_cc_xml(data, opts) {
	var d = [];
	if(!data) return d;
	var l = 0, i = 1;
	(data.match(tagregex)||[]).forEach(function(x) {
		var y = parsexmltag(x);
		switch(y[0]) {
			case '<?xml': break;
			/* 18.6.2  calcChain CT_CalcChain 1 */
			case '<calcChain': case '<calcChain>': case '</calcChain>': break;
			/* 18.6.1  c CT_CalcCell 1 */
			case '<c': delete y[0]; if(y.i) i = y.i; else y.i = i; d.push(y); break;
		}
	});
	return d;
}

function write_cc_xml(data, opts) { }
/* [MS-XLSB] 2.6.4.1 */
function parse_BrtCalcChainItem$(data, length) {
	var out = {};
	out.i = data.read_shift(4);
	var cell = {};
	cell.r = data.read_shift(4);
	cell.c = data.read_shift(4);
	out.r = encode_cell(cell);
	var flags = data.read_shift(1);
	if(flags & 0x2) out.l = '1';
	if(flags & 0x8) out.a = '1';
	return out;
}

/* 18.6 Calculation Chain */
function parse_cc_bin(data, opts) {
	var out = [];
	var pass = false;
	recordhopper(data, function hopper_cc(val, R_n, RT) {
		switch(RT) {
			case 0x003F: /* 'BrtCalcChainItem$' */
				out.push(val); break;

			default:
				if((R_n||"").indexOf("Begin") > 0){/* empty */}
				else if((R_n||"").indexOf("End") > 0){/* empty */}
				else if(!pass || opts.WTF) throw new Error("Unexpected record " + RT + " " + R_n);
		}
	});
	return out;
}

function write_cc_bin(data, opts) { }
RELS.IMG = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image";
RELS.DRAW = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/drawing";
/* 20.5 DrawingML - SpreadsheetML Drawing */
function parse_drawing(data, rels) {
	if(!data) return "??";
	/*
	  Chartsheet Drawing:
	   - 20.5.2.35 wsDr CT_Drawing
	    - 20.5.2.1  absoluteAnchor CT_AbsoluteAnchor
	     - 20.5.2.16 graphicFrame CT_GraphicalObjectFrame
	      - 20.1.2.2.16 graphic CT_GraphicalObject
	       - 20.1.2.2.17 graphicData CT_GraphicalObjectData
          - chart reference
	   the actual type is based on the URI of the graphicData
		TODO: handle embedded charts and other types of graphics
	*/
	var id = (data.match(/<c:chart [^>]*r:id="([^"]*)"/)||["",""])[1];

	return rels['!id'][id].Target;
}

/* L.5.5.2 SpreadsheetML Comments + VML Schema */
var _shapeid = 1024;
function write_comments_vml(rId, comments) {
	var csize = [21600, 21600];
	/* L.5.2.1.2 Path Attribute */
	var bbox = ["m0,0l0",csize[1],csize[0],csize[1],csize[0],"0xe"].join(",");
	var o = [
		writextag("xml", null, { 'xmlns:v': XLMLNS.v, 'xmlns:o': XLMLNS.o, 'xmlns:x': XLMLNS.x, 'xmlns:mv': XLMLNS.mv }).replace(/\/>/,">"),
		writextag("o:shapelayout", writextag("o:idmap", null, {'v:ext':"edit", 'data':rId}), {'v:ext':"edit"}),
		writextag("v:shapetype", [
			writextag("v:stroke", null, {joinstyle:"miter"}),
			writextag("v:path", null, {gradientshapeok:"t", 'o:connecttype':"rect"})
		].join(""), {id:"_x0000_t202", 'o:spt':202, coordsize:csize.join(","),path:bbox})
	];
	while(_shapeid < rId * 1000) _shapeid += 1000;

	comments.map(function(x) { return decode_cell(x[0]); }).forEach(function(c,i) { o = o.concat([
	'<v:shape' + wxt_helper({
		id:'_x0000_s' + (++_shapeid),
		type:"#_x0000_t202",
		style:"position:absolute; margin-left:80pt;margin-top:5pt;width:104pt;height:64pt;z-index:10;visibility:hidden",
		fillcolor:"#ECFAD4",
		strokecolor:"#edeaa1"
	}) + '>',
		writextag('v:fill', writextag("o:fill", null, {type:"gradientUnscaled", 'v:ext':"view"}), {'color2':"#BEFF82", 'angle':"-180", 'type':"gradient"}),
		writextag("v:shadow", null, {on:"t", 'obscured':"t"}),
		writextag("v:path", null, {'o:connecttype':"none"}),
		'<v:textbox><div style="text-align:left"></div></v:textbox>',
		'<x:ClientData ObjectType="Note">',
			'<x:MoveWithCells/>',
			'<x:SizeWithCells/>',
			/* Part 4 19.4.2.3 Anchor (Anchor) */
			writetag('x:Anchor', [c.c, 0, c.r, 0, c.c+3, 100, c.r+5, 100].join(",")),
			writetag('x:AutoFill', "False"),
			writetag('x:Row', String(c.r)),
			writetag('x:Column', String(c.c)),
			'<x:Visible/>',
		'</x:ClientData>',
	'</v:shape>'
	]); });
	o.push('</xml>');
	return o.join("");
}

RELS.CMNT = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments";

function parse_comments(zip, dirComments, sheets, sheetRels, opts) {
	for(var i = 0; i != dirComments.length; ++i) {
		var canonicalpath=dirComments[i];
		var comments=parse_cmnt(getzipdata(zip, canonicalpath.replace(/^\//,''), true), canonicalpath, opts);
		if(!comments || !comments.length) continue;
		// find the sheets targeted by these comments
		var sheetNames = keys(sheets);
		for(var j = 0; j != sheetNames.length; ++j) {
			var sheetName = sheetNames[j];
			var rels = sheetRels[sheetName];
			if(rels) {
				var rel = rels[canonicalpath];
				if(rel) insertCommentsIntoSheet(sheetName, sheets[sheetName], comments);
			}
		}
	}
}

function insertCommentsIntoSheet(sheetName, sheet, comments) {
	var dense = Array.isArray(sheet);
	var cell, r;
	comments.forEach(function(comment) {
		if(dense) {
			r = decode_cell(comment.ref);
			if(!sheet[r.r]) sheet[r.r] = [];
			cell = sheet[r.r][r.c];
		} else cell = sheet[comment.ref];
		if (!cell) {
			cell = {};
			if(dense) sheet[r.r][r.c] = cell;
			else sheet[comment.ref] = cell;
			var range = safe_decode_range(sheet["!ref"]||"BDWGO1000001:A1");
			var thisCell = decode_cell(comment.ref);
			if(range.s.r > thisCell.r) range.s.r = thisCell.r;
			if(range.e.r < thisCell.r) range.e.r = thisCell.r;
			if(range.s.c > thisCell.c) range.s.c = thisCell.c;
			if(range.e.c < thisCell.c) range.e.c = thisCell.c;
			var encoded = encode_range(range);
			if (encoded !== sheet["!ref"]) sheet["!ref"] = encoded;
		}

		if (!cell.c) cell.c = [];
		var o = ({a: comment.author, t: comment.t, r: comment.r});
		if(comment.h) o.h = comment.h;
		cell.c.push(o);
	});
}

/* 18.7 Comments */
function parse_comments_xml(data, opts) {
	/* 18.7.6 CT_Comments */
	if(data.match(/<(?:\w+:)?comments *\/>/)) return [];
	var authors = [];
	var commentList = [];
	var authtag = data.match(/<(?:\w+:)?authors>([^\u2603]*)<\/(?:\w+:)?authors>/);
	if(authtag && authtag[1]) authtag[1].split(/<\/\w*:?author>/).forEach(function(x) {
		if(x === "" || x.trim() === "") return;
		var a = x.match(/<(?:\w+:)?author[^>]*>(.*)/);
		if(a) authors.push(a[1]);
	});
	var cmnttag = data.match(/<(?:\w+:)?commentList>([^\u2603]*)<\/(?:\w+:)?commentList>/);
	if(cmnttag && cmnttag[1]) cmnttag[1].split(/<\/\w*:?comment>/).forEach(function(x, index) {
		if(x === "" || x.trim() === "") return;
		var cm = x.match(/<(?:\w+:)?comment[^>]*>/);
		if(!cm) return;
		var y = parsexmltag(cm[0]);
		var comment = ({ author: y.authorId && authors[y.authorId] ? authors[y.authorId] : "sheetjsghost", ref: y.ref, guid: y.guid });
		var cell = decode_cell(y.ref);
		if(opts.sheetRows && opts.sheetRows <= cell.r) return;
		var textMatch = x.match(/<(?:\w+:)?text>([^\u2603]*)<\/(?:\w+:)?text>/);
		var rt = !!textMatch && !!textMatch[1] && parse_si(textMatch[1]) || {r:"",t:"",h:""};
		comment.r = rt.r;
		if(rt.r == "<t></t>") rt.t = rt.h = "";
		comment.t = rt.t.replace(/\r\n/g,"\n").replace(/\r/g,"\n");
		if(opts.cellHTML) comment.h = rt.h;
		commentList.push(comment);
	});
	return commentList;
}

var CMNT_XML_ROOT = writextag('comments', null, { 'xmlns': XMLNS.main[0] });
function write_comments_xml(data, opts) {
	var o = [XML_HEADER, CMNT_XML_ROOT];

	var iauthor = [];
	o.push("<authors>");
	data.map(function(x) { return x[1]; }).forEach(function(comment) {
		comment.map(function(x) { return escapexml(x.a); }).forEach(function(a) {
			if(iauthor.indexOf(a) > -1) return;
			iauthor.push(a);
			o.push("<author>" + a + "</author>");
		});
	});
	o.push("</authors>");
	o.push("<commentList>");
	data.forEach(function(d) {
		d[1].forEach(function(c) {
			/* 18.7.3 CT_Comment */
			o.push('<comment ref="' + d[0] + '" authorId="' + iauthor.indexOf(escapexml(c.a)) + '"><text>');
			o.push(writetag("t", c.t == null ? "" : c.t));
			o.push('</text></comment>');
		});
	});
	o.push("</commentList>");
	if(o.length>2) { o[o.length] = ('</comments>'); o[1]=o[1].replace("/>",">"); }
	return o.join("");
}
/* [MS-XLSB] 2.4.28 BrtBeginComment */
function parse_BrtBeginComment(data, length) {
	var out = {};
	out.iauthor = data.read_shift(4);
	var rfx = parse_UncheckedRfX(data, 16);
	out.rfx = rfx.s;
	out.ref = encode_cell(rfx.s);
	data.l += 16; /*var guid = parse_GUID(data); */
	return out;
}
function write_BrtBeginComment(data, o) {
	if(o == null) o = new_buf(36);
	o.write_shift(4, data[1].iauthor);
	write_UncheckedRfX((data[0]), o);
	o.write_shift(4, 0);
	o.write_shift(4, 0);
	o.write_shift(4, 0);
	o.write_shift(4, 0);
	return o;
}

/* [MS-XLSB] 2.4.324 BrtCommentAuthor */
var parse_BrtCommentAuthor = parse_XLWideString;

/* [MS-XLSB] 2.1.7.8 Comments */
function parse_comments_bin(data, opts) {
	var out = [];
	var authors = [];
	var c = {};
	var pass = false;
	recordhopper(data, function hopper_cmnt(val, R_n, RT) {
		switch(RT) {
			case 0x0278: /* 'BrtCommentAuthor' */
				authors.push(val); break;
			case 0x027B: /* 'BrtBeginComment' */
				c = val; break;
			case 0x027D: /* 'BrtCommentText' */
				c.t = val.t; c.h = val.h; c.r = val.r; break;
			case 0x027C: /* 'BrtEndComment' */
				c.author = authors[c.iauthor];
				delete c.iauthor;
				if(opts.sheetRows && opts.sheetRows <= c.rfx.r) break;
				if(!c.t) c.t = "";
				delete c.rfx; out.push(c); break;

			/* case 'BrtUid': */

			case 0x0023: /* 'BrtFRTBegin' */
				pass = true; break;
			case 0x0024: /* 'BrtFRTEnd' */
				pass = false; break;
			case 0x0025: /* 'BrtACBegin' */ break;
			case 0x0026: /* 'BrtACEnd' */ break;


			default:
				if((R_n||"").indexOf("Begin") > 0){/* empty */}
				else if((R_n||"").indexOf("End") > 0){/* empty */}
				else if(!pass || opts.WTF) throw new Error("Unexpected record " + RT + " " + R_n);
		}
	});
	return out;
}

function write_comments_bin(data, opts) {
	var ba = buf_array();
	var iauthor = [];
	write_record(ba, "BrtBeginComments");
	{ /* COMMENTAUTHORS */
		write_record(ba, "BrtBeginCommentAuthors");
		data.forEach(function(comment) {
			comment[1].forEach(function(c) {
				if(iauthor.indexOf(c.a) > -1) return;
				iauthor.push(c.a.substr(0,54));
				write_record(ba, "BrtCommentAuthor", write_XLWideString(c.a.substr(0, 54)));
			});
		});
		write_record(ba, "BrtEndCommentAuthors");
	}
	{ /* COMMENTLIST */
		write_record(ba, "BrtBeginCommentList");
		data.forEach(function(comment) {
			comment[1].forEach(function(c) {
				c.iauthor = iauthor.indexOf(c.a);
				var range = {s:decode_cell(comment[0]),e:decode_cell(comment[0])};
				write_record(ba, "BrtBeginComment", write_BrtBeginComment([range, c]));
				if(c.t && c.t.length > 0) write_record(ba, "BrtCommentText", write_BrtCommentText(c));
				write_record(ba, "BrtEndComment");
				delete c.iauthor;
			});
		});
		write_record(ba, "BrtEndCommentList");
	}
	write_record(ba, "BrtEndComments");
	return ba.end();
}
RELS.DS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/dialogsheet";
RELS.MS = "http://schemas.microsoft.com/office/2006/relationships/xlMacrosheet";

/* macro and dialog sheet stubs */
function parse_ds_bin() { return {'!type':'dialog'}; }
function parse_ds_xml() { return {'!type':'dialog'}; }
function parse_ms_bin() { return {'!type':'macro'}; }
function parse_ms_xml() { return {'!type':'macro'}; }
/* TODO: it will be useful to parse the function str */
var rc_to_a1 = (function(){
	var rcregex = /(^|[^A-Za-z])R(\[?)(-?\d+|)\]?C(\[?)(-?\d+|)\]?/g;
	var rcbase = ({r:0,c:0});
	function rcfunc($$,$1,$2,$3,$4,$5) {
		var R = $3.length>0?parseInt($3,10)|0:0, C = $5.length>0?parseInt($5,10)|0:0;
		if(C<0 && $4.length === 0) C=0;
		var cRel = false, rRel = false;
		if($4.length > 0 || $5.length == 0) cRel = true; if(cRel) C += rcbase.c; else --C;
		if($2.length > 0 || $3.length == 0) rRel = true; if(rRel) R += rcbase.r; else --R;
		return $1 + (cRel ? "" : "$") + encode_col(C) + (rRel ? "" : "$") + encode_row(R);
	}
	return function rc_to_a1(fstr, base) {
		rcbase = base;
		return fstr.replace(rcregex, rcfunc);
	};
})();

var crefregex = /(^|[^._A-Z0-9])([$]?)([A-Z]{1,2}|[A-W][A-Z]{2}|X[A-E][A-Z]|XF[A-D])([$]?)([1-9]\d{0,5}|10[0-3]\d{4}|104[0-7]\d{3}|1048[0-4]\d{2}|10485[0-6]\d|104857[0-6])(?![_.\(A-Za-z0-9])/g;
var a1_to_rc =(function(){
	return function a1_to_rc(fstr, base) {
		return fstr.replace(crefregex, function($0, $1, $2, $3, $4, $5, off, str) {
			/* TODO: handle fixcol / fixrow */
			var c = decode_col($3) - base.c;
			var r = decode_row($5) - base.r;
			return $1 + "R" + (r == 0 ? "" : "[" + r + "]") + "C" + (c == 0 ? "" : "[" + c + "]");
		});
	};
})();

/* no defined name can collide with a valid cell address A1:XFD1048576 ... except LOG10! */
function shift_formula_str(f, delta) {
	return f.replace(crefregex, function($0, $1, $2, $3, $4, $5, off, str) {
		return $1+($2=="$" ? $2+$3 : encode_col(decode_col($3)+delta.c))+($4=="$" ? $4+$5 : encode_row(decode_row($5) + delta.r));
	});
}

function shift_formula_xlsx(f, range, cell) {
	var r = decode_range(range), s = r.s, c = decode_cell(cell);
	var delta = {r:c.r - s.r, c:c.c - s.c};
	return shift_formula_str(f, delta);
}
/* --- formula references point to MS-XLS --- */
/* Small helpers */
function parseread(l) { return function(blob, length) { blob.l+=l; return; }; }
function parseread1(blob) { blob.l+=1; return; }

/* Rgce Helpers */

/* 2.5.51 */
function parse_ColRelU(blob, length) {
	var c = blob.read_shift(length == 1 ? 1 : 2);
	return [c & 0x3FFF, (c >> 14) & 1, (c >> 15) & 1];
}

/* [MS-XLS] 2.5.198.105 */
/* [MS-XLSB] 2.5.97.89 */
function parse_RgceArea(blob, length, opts) {
	var w = 2;
	if(opts) {
		if(opts.biff >= 2 && opts.biff <= 5) return parse_RgceArea_BIFF2(blob, length, opts);
		else if(opts.biff == 12) w = 4;
	}
	var r=blob.read_shift(w), R=blob.read_shift(w);
	var c=parse_ColRelU(blob, 2);
	var C=parse_ColRelU(blob, 2);
	return { s:{r:r, c:c[0], cRel:c[1], rRel:c[2]}, e:{r:R, c:C[0], cRel:C[1], rRel:C[2]} };
}
/* BIFF 2-5 encodes flags in the row field */
function parse_RgceArea_BIFF2(blob/*, length, opts*/) {
	var r=parse_ColRelU(blob, 2), R=parse_ColRelU(blob, 2);
	var c=blob.read_shift(1);
	var C=blob.read_shift(1);
	return { s:{r:r[0], c:c, cRel:r[1], rRel:r[2]}, e:{r:R[0], c:C, cRel:R[1], rRel:R[2]} };
}

/* 2.5.198.105 TODO */
function parse_RgceAreaRel(blob, length/*, opts*/) {
	var r=blob.read_shift(length == 12 ? 4 : 2), R=blob.read_shift(length == 12 ? 4 : 2);
	var c=parse_ColRelU(blob, 2);
	var C=parse_ColRelU(blob, 2);
	return { s:{r:r, c:c[0], cRel:c[1], rRel:c[2]}, e:{r:R, c:C[0], cRel:C[1], rRel:C[2]} };
}

/* 2.5.198.109 */
function parse_RgceLoc(blob, length, opts) {
	if(opts && opts.biff >= 2 && opts.biff <= 5) return parse_RgceLoc_BIFF2(blob, length, opts);
	var r = blob.read_shift(opts && opts.biff == 12 ? 4 : 2);
	var c = parse_ColRelU(blob, 2);
	return {r:r, c:c[0], cRel:c[1], rRel:c[2]};
}
function parse_RgceLoc_BIFF2(blob, length, opts) {
	var r = parse_ColRelU(blob, 2);
	var c = blob.read_shift(1);
	return {r:r[0], c:c, cRel:r[1], rRel:r[2]};
}

/* [MS-XLS] 2.5.198.111 TODO */
/* [MS-XLSB] 2.5.97.92 TODO */
function parse_RgceLocRel(blob, length, opts) {
	var biff = opts && opts.biff ? opts.biff : 8;
	if(biff >= 2 && biff <= 5) return parse_RgceLocRel_BIFF2(blob, length, opts);
	var r = blob.read_shift(biff >= 12 ? 4 : 2);
	var cl = blob.read_shift(2);
	var cRel = (cl & 0x8000) >> 15, rRel = (cl & 0x4000) >> 14;
	cl &= 0x3FFF;
	if(rRel == 1) while(r > 0x7FFFF) r -= 0x100000;
	if(cRel == 1) while(cl > 0x1FFF) cl = cl - 0x4000;
	return {r:r,c:cl,cRel:cRel,rRel:rRel};
}
function parse_RgceLocRel_BIFF2(blob, length) {
	var rl = blob.read_shift(2);
	var c = blob.read_shift(1);
	var rRel = (rl & 0x8000) >> 15, cRel = (rl & 0x4000) >> 14;
	rl &= 0x3FFF;
	if(rRel == 1 && rl >= 0x2000) rl = rl - 0x4000;
	if(cRel == 1 && c >= 0x80) c = c - 0x100;
	return {r:rl,c:c,cRel:cRel,rRel:rRel};
}

/* Ptg Tokens */

/* 2.5.198.27 */
function parse_PtgArea(blob, length, opts) {
	var type = (blob[blob.l++] & 0x60) >> 5;
	var area = parse_RgceArea(blob, opts.biff >= 2 && opts.biff <= 5 ? 6 : 8, opts);
	return [type, area];
}

/* [MS-XLS] 2.5.198.28 */
/* [MS-XLSB] 2.5.97.19 */
function parse_PtgArea3d(blob, length, opts) {
	var type = (blob[blob.l++] & 0x60) >> 5;
	var ixti = blob.read_shift(2, 'i');
	var w = 8;
	if(opts) switch(opts.biff) {
		case 5: blob.l += 12; w = 6; break;
		case 12: w = 12; break;
	}
	var area = parse_RgceArea(blob, w, opts);
	return [type, ixti, area];
}

/* 2.5.198.29 */
function parse_PtgAreaErr(blob, length, opts) {
	var type = (blob[blob.l++] & 0x60) >> 5;
	blob.l += opts && opts.biff > 8 ? 12 : 8;
	return [type];
}
/* 2.5.198.30 */
function parse_PtgAreaErr3d(blob, length, opts) {
	var type = (blob[blob.l++] & 0x60) >> 5;
	var ixti = blob.read_shift(2);
	var w = 8;
	if(opts) switch(opts.biff) {
		case 5: blob.l += 12; w = 6; break;
		case 12: w = 12; break;
	}
	blob.l += w;
	return [type, ixti];
}

/* 2.5.198.31 */
function parse_PtgAreaN(blob, length, opts) {
	var type = (blob[blob.l++] & 0x60) >> 5;
	var area = parse_RgceAreaRel(blob, opts && opts.biff > 8 ? 12 : 8, opts);
	return [type, area];
}

/* [MS-XLS] 2.5.198.32 */
/* [MS-XLSB] 2.5.97.23 */
function parse_PtgArray(blob, length, opts) {
	var type = (blob[blob.l++] & 0x60) >> 5;
	blob.l += opts.biff == 2 ? 6 : opts.biff == 12 ? 14 : 7;
	return [type];
}

/* 2.5.198.33 */
function parse_PtgAttrBaxcel(blob, length) {
	var bitSemi = blob[blob.l+1] & 0x01; /* 1 = volatile */
	var bitBaxcel = 1;
	blob.l += 4;
	return [bitSemi, bitBaxcel];
}

/* 2.5.198.34 */
function parse_PtgAttrChoose(blob, length, opts) {
	blob.l +=2;
	var offset = blob.read_shift(opts && opts.biff == 2 ? 1 : 2);
	var o = [];
	/* offset is 1 less than the number of elements */
	for(var i = 0; i <= offset; ++i) o.push(blob.read_shift(opts && opts.biff == 2 ? 1 : 2));
	return o;
}

/* 2.5.198.35 */
function parse_PtgAttrGoto(blob, length, opts) {
	var bitGoto = (blob[blob.l+1] & 0xFF) ? 1 : 0;
	blob.l += 2;
	return [bitGoto, blob.read_shift(opts && opts.biff == 2 ? 1 : 2)];
}

/* 2.5.198.36 */
function parse_PtgAttrIf(blob, length, opts) {
	var bitIf = (blob[blob.l+1] & 0xFF) ? 1 : 0;
	blob.l += 2;
	return [bitIf, blob.read_shift(opts && opts.biff == 2 ? 1 : 2)];
}

/* [MS-XLSB] 2.5.97.28 */
function parse_PtgAttrIfError(blob, length) {
	var bitIf = (blob[blob.l+1] & 0xFF) ? 1 : 0;
	blob.l += 2;
	return [bitIf, blob.read_shift(2)];
}

/* 2.5.198.37 */
function parse_PtgAttrSemi(blob, length, opts) {
	var bitSemi = (blob[blob.l+1] & 0xFF) ? 1 : 0;
	blob.l += opts && opts.biff == 2 ? 3 : 4;
	return [bitSemi];
}

/* 2.5.198.40 (used by PtgAttrSpace and PtgAttrSpaceSemi) */
function parse_PtgAttrSpaceType(blob, length) {
	var type = blob.read_shift(1), cch = blob.read_shift(1);
	return [type, cch];
}

/* 2.5.198.38 */
function parse_PtgAttrSpace(blob, length) {
	blob.read_shift(2);
	return parse_PtgAttrSpaceType(blob, 2);
}

/* 2.5.198.39 */
function parse_PtgAttrSpaceSemi(blob, length) {
	blob.read_shift(2);
	return parse_PtgAttrSpaceType(blob, 2);
}

/* 2.5.198.84 TODO */
function parse_PtgRef(blob, length, opts) {
	var ptg = blob[blob.l] & 0x1F;
	var type = (blob[blob.l] & 0x60)>>5;
	blob.l += 1;
	var loc = parse_RgceLoc(blob, 0, opts);
	return [type, loc];
}

/* 2.5.198.88 TODO */
function parse_PtgRefN(blob, length, opts) {
	var type = (blob[blob.l] & 0x60)>>5;
	blob.l += 1;
	var loc = parse_RgceLocRel(blob, 0, opts);
	return [type, loc];
}

/* 2.5.198.85 TODO */
function parse_PtgRef3d(blob, length, opts) {
	var type = (blob[blob.l] & 0x60)>>5;
	blob.l += 1;
	var ixti = blob.read_shift(2); // XtiIndex
	var loc = parse_RgceLoc(blob, 0, opts); // TODO: or RgceLocRel
	return [type, ixti, loc];
}


/* 2.5.198.62 TODO */
function parse_PtgFunc(blob, length, opts) {
	var ptg = blob[blob.l] & 0x1F;
	var type = (blob[blob.l] & 0x60)>>5;
	blob.l += 1;
	var iftab = blob.read_shift(opts && opts.biff <= 3 ? 1 : 2);
	return [FtabArgc[iftab], Ftab[iftab], type];
}
/* 2.5.198.63 TODO */
function parse_PtgFuncVar(blob, length, opts) {
	blob.l++;
	var cparams = blob.read_shift(1), tab = opts && opts.biff <= 3 ? [0, blob.read_shift(1)]: parsetab(blob);
	return [cparams, (tab[0] === 0 ? Ftab : Cetab)[tab[1]]];
}

function parsetab(blob, length) {
	return [blob[blob.l+1]>>7, blob.read_shift(2) & 0x7FFF];
}

/* 2.5.198.41 */
function parse_PtgAttrSum(blob, length, opts) {
	blob.l += opts && opts.biff == 2 ? 3 : 4; return;
}

/* 2.5.198.43 */
var parse_PtgConcat = parseread1;

/* 2.5.198.58 */
function parse_PtgExp(blob, length, opts) {
	blob.l++;
	if(opts && opts.biff == 12) return [blob.read_shift(4, 'i'), 0];
	var row = blob.read_shift(2);
	var col = blob.read_shift(opts && opts.biff == 2 ? 1 : 2);
	return [row, col];
}

/* 2.5.198.57 */
function parse_PtgErr(blob, length) { blob.l++; return BErr[blob.read_shift(1)]; }

/* 2.5.198.66 */
function parse_PtgInt(blob, length) { blob.l++; return blob.read_shift(2); }

/* 2.5.198.42 */
function parse_PtgBool(blob, length) { blob.l++; return blob.read_shift(1)!==0;}

/* 2.5.198.79 */
function parse_PtgNum(blob, length) { blob.l++; return parse_Xnum(blob, 8); }

/* 2.5.198.89 */
function parse_PtgStr(blob, length, opts) { blob.l++; return parse_ShortXLUnicodeString(blob, length-1, opts); }

/* [MS-XLS] 2.5.192.112 + 2.5.192.11{3,4,5,6,7} */
/* [MS-XLSB] 2.5.97.93 + 2.5.97.9{4,5,6,7} */
function parse_SerAr(blob, biff) {
	var val = [blob.read_shift(1)];
	if(biff == 12) switch(val[0]) {
		case 0x02: val[0] = 0x04; break; /* SerBool */
		case 0x04: val[0] = 0x10; break; /* SerErr */
		case 0x00: val[0] = 0x01; break; /* SerNum */
		case 0x01: val[0] = 0x02; break; /* SerStr */
	}
	switch(val[0]) {
		/* 2.5.192.113 */
		case 0x04: /* SerBool -- boolean */
			val[1] = parsebool(blob, 1) ? 'TRUE' : 'FALSE';
			blob.l += 7; break;
		/* 2.5.192.114 */
		case 0x10: /* SerErr -- error */
			val[1] = BErr[blob[blob.l]];
			blob.l += 8; break;
		/* 2.5.192.115 */
		case 0x00: /* SerNil -- honestly, I'm not sure how to reproduce this */
			blob.l += 8; break;
		/* 2.5.192.116 */
		case 0x01: /* SerNum -- Xnum */
			val[1] = parse_Xnum(blob, 8); break;
		/* 2.5.192.117 */
		case 0x02: /* SerStr -- XLUnicodeString (<256 chars) */
			val[1] = parse_XLUnicodeString2(blob, 0, {biff:biff > 0 && biff < 8 ? 2 : biff}); break;
		// default: throw "Bad SerAr: " + val[0]; /* Unreachable */
	}
	return val;
}

/* 2.5.198.61 */
function parse_PtgExtraMem(blob, cce) {
	var count = blob.read_shift(2);
	var out = [];
	for(var i = 0; i != count; ++i) out.push(parse_Ref8U(blob, 8));
	return out;
}

/* 2.5.198.59 */
function parse_PtgExtraArray(blob, length, opts) {
	var rows = 0, cols = 0;
	if(opts.biff == 12) {
		rows = blob.read_shift(4); // DRw
		cols = blob.read_shift(4); // DCol
	} else {
		cols = 1 + blob.read_shift(1); //DColByteU
		rows = 1 + blob.read_shift(2); //DRw
	}
	if(opts.biff >= 2 && opts.biff < 8) { --rows; if(--cols == 0) cols = 0x100; }
	// $FlowIgnore
	for(var i = 0, o=[]; i != rows && (o[i] = []); ++i)
		for(var j = 0; j != cols; ++j) o[i][j] = parse_SerAr(blob, opts.biff);
	return o;
}

/* 2.5.198.76 */
function parse_PtgName(blob, length, opts) {
	var type = (blob.read_shift(1) >>> 5) & 0x03;
	var w = (!opts || (opts.biff >= 8)) ? 4 : 2;
	var nameindex = blob.read_shift(w);
	switch(opts.biff) {
		case 2: blob.l += 5; break;
		case 3: case 4: blob.l += 8; break;
		case 5: blob.l += 12; break;
	}
	return [type, 0, nameindex];
}

/* 2.5.198.77 */
function parse_PtgNameX(blob, length, opts) {
	if(opts.biff == 5) return parse_PtgNameX_BIFF5(blob, length, opts);
	var type = (blob.read_shift(1) >>> 5) & 0x03;
	var ixti = blob.read_shift(2); // XtiIndex
	var nameindex = blob.read_shift(4);
	return [type, ixti, nameindex];
}
function parse_PtgNameX_BIFF5(blob, length, opts) {
	var type = (blob.read_shift(1) >>> 5) & 0x03;
	var ixti = blob.read_shift(2, 'i'); // XtiIndex
	blob.l += 8;
	var nameindex = blob.read_shift(2);
	blob.l += 12;
	return [type, ixti, nameindex];
}

/* 2.5.198.70 */
function parse_PtgMemArea(blob, length, opts) {
	var type = (blob.read_shift(1) >>> 5) & 0x03;
	blob.l += (opts && opts.biff == 2 ? 3 : 4);
	var cce = blob.read_shift(opts && opts.biff == 2 ? 1 : 2);
	return [type, cce];
}

/* 2.5.198.72 */
function parse_PtgMemFunc(blob, length, opts) {
	var type = (blob.read_shift(1) >>> 5) & 0x03;
	var cce = blob.read_shift(opts && opts.biff == 2 ? 1 : 2);
	return [type, cce];
}


/* 2.5.198.86 */
function parse_PtgRefErr(blob, length, opts) {
	var type = (blob.read_shift(1) >>> 5) & 0x03;
	blob.l += 4;
	if(opts.biff == 12) blob.l += 2;
	return [type];
}

/* 2.5.198.87 */
function parse_PtgRefErr3d(blob, length, opts) {
	var type = (blob[blob.l++] & 0x60) >> 5;
	var ixti = blob.read_shift(2);
	var w = 4;
	if(opts) switch(opts.biff) {
		case 5: throw new Error("PtgRefErr3d -- 5"); // TODO: find test case
		case 12: w = 6; break;
	}
	blob.l += w;
	return [type, ixti];
}

/* 2.5.198.26 */
var parse_PtgAdd = parseread1;
/* 2.5.198.45 */
var parse_PtgDiv = parseread1;
/* 2.5.198.56 */
var parse_PtgEq = parseread1;
/* 2.5.198.64 */
var parse_PtgGe = parseread1;
/* 2.5.198.65 */
var parse_PtgGt = parseread1;
/* 2.5.198.67 */
var parse_PtgIsect = parseread1;
/* 2.5.198.68 */
var parse_PtgLe = parseread1;
/* 2.5.198.69 */
var parse_PtgLt = parseread1;
/* 2.5.198.74 */
var parse_PtgMissArg = parseread1;
/* 2.5.198.75 */
var parse_PtgMul = parseread1;
/* 2.5.198.78 */
var parse_PtgNe = parseread1;
/* 2.5.198.80 */
var parse_PtgParen = parseread1;
/* 2.5.198.81 */
var parse_PtgPercent = parseread1;
/* 2.5.198.82 */
var parse_PtgPower = parseread1;
/* 2.5.198.83 */
var parse_PtgRange = parseread1;
/* 2.5.198.90 */
var parse_PtgSub = parseread1;
/* 2.5.198.93 */
var parse_PtgUminus = parseread1;
/* 2.5.198.94 */
var parse_PtgUnion = parseread1;
/* 2.5.198.95 */
var parse_PtgUplus = parseread1;

/* 2.5.198.71 */
var parse_PtgMemErr = parsenoop;
/* 2.5.198.73 */
var parse_PtgMemNoMem = parsenoop;
/* 2.5.198.92 */
var parse_PtgTbl = parsenoop;

/* 2.5.198.25 */
var PtgTypes = {
0x01: { n:'PtgExp', f:parse_PtgExp },
0x02: { n:'PtgTbl', f:parse_PtgTbl },
0x03: { n:'PtgAdd', f:parse_PtgAdd },
0x04: { n:'PtgSub', f:parse_PtgSub },
0x05: { n:'PtgMul', f:parse_PtgMul },
0x06: { n:'PtgDiv', f:parse_PtgDiv },
0x07: { n:'PtgPower', f:parse_PtgPower },
0x08: { n:'PtgConcat', f:parse_PtgConcat },
0x09: { n:'PtgLt', f:parse_PtgLt },
0x0A: { n:'PtgLe', f:parse_PtgLe },
0x0B: { n:'PtgEq', f:parse_PtgEq },
0x0C: { n:'PtgGe', f:parse_PtgGe },
0x0D: { n:'PtgGt', f:parse_PtgGt },
0x0E: { n:'PtgNe', f:parse_PtgNe },
0x0F: { n:'PtgIsect', f:parse_PtgIsect },
0x10: { n:'PtgUnion', f:parse_PtgUnion },
0x11: { n:'PtgRange', f:parse_PtgRange },
0x12: { n:'PtgUplus', f:parse_PtgUplus },
0x13: { n:'PtgUminus', f:parse_PtgUminus },
0x14: { n:'PtgPercent', f:parse_PtgPercent },
0x15: { n:'PtgParen', f:parse_PtgParen },
0x16: { n:'PtgMissArg', f:parse_PtgMissArg },
0x17: { n:'PtgStr', f:parse_PtgStr },
0x1C: { n:'PtgErr', f:parse_PtgErr },
0x1D: { n:'PtgBool', f:parse_PtgBool },
0x1E: { n:'PtgInt', f:parse_PtgInt },
0x1F: { n:'PtgNum', f:parse_PtgNum },
0x20: { n:'PtgArray', f:parse_PtgArray },
0x21: { n:'PtgFunc', f:parse_PtgFunc },
0x22: { n:'PtgFuncVar', f:parse_PtgFuncVar },
0x23: { n:'PtgName', f:parse_PtgName },
0x24: { n:'PtgRef', f:parse_PtgRef },
0x25: { n:'PtgArea', f:parse_PtgArea },
0x26: { n:'PtgMemArea', f:parse_PtgMemArea },
0x27: { n:'PtgMemErr', f:parse_PtgMemErr },
0x28: { n:'PtgMemNoMem', f:parse_PtgMemNoMem },
0x29: { n:'PtgMemFunc', f:parse_PtgMemFunc },
0x2A: { n:'PtgRefErr', f:parse_PtgRefErr },
0x2B: { n:'PtgAreaErr', f:parse_PtgAreaErr },
0x2C: { n:'PtgRefN', f:parse_PtgRefN },
0x2D: { n:'PtgAreaN', f:parse_PtgAreaN },
0x39: { n:'PtgNameX', f:parse_PtgNameX },
0x3A: { n:'PtgRef3d', f:parse_PtgRef3d },
0x3B: { n:'PtgArea3d', f:parse_PtgArea3d },
0x3C: { n:'PtgRefErr3d', f:parse_PtgRefErr3d },
0x3D: { n:'PtgAreaErr3d', f:parse_PtgAreaErr3d },
0xFF: {}
};
/* These are duplicated in the PtgTypes table */
var PtgDupes = {
0x40: 0x20, 0x60: 0x20,
0x41: 0x21, 0x61: 0x21,
0x42: 0x22, 0x62: 0x22,
0x43: 0x23, 0x63: 0x23,
0x44: 0x24, 0x64: 0x24,
0x45: 0x25, 0x65: 0x25,
0x46: 0x26, 0x66: 0x26,
0x47: 0x27, 0x67: 0x27,
0x48: 0x28, 0x68: 0x28,
0x49: 0x29, 0x69: 0x29,
0x4A: 0x2A, 0x6A: 0x2A,
0x4B: 0x2B, 0x6B: 0x2B,
0x4C: 0x2C, 0x6C: 0x2C,
0x4D: 0x2D, 0x6D: 0x2D,
0x59: 0x39, 0x79: 0x39,
0x5A: 0x3A, 0x7A: 0x3A,
0x5B: 0x3B, 0x7B: 0x3B,
0x5C: 0x3C, 0x7C: 0x3C,
0x5D: 0x3D, 0x7D: 0x3D
};
(function(){for(var y in PtgDupes) PtgTypes[y] = PtgTypes[PtgDupes[y]];})();

var Ptg18 = {
//	0x19: { n:'PtgList', f:parse_PtgList }, // TODO
//	0x1D: { n:'PtgSxName', f:parse_PtgSxName }, // TODO
};
var Ptg19 = {
0x01: { n:'PtgAttrSemi', f:parse_PtgAttrSemi },
0x02: { n:'PtgAttrIf', f:parse_PtgAttrIf },
0x04: { n:'PtgAttrChoose', f:parse_PtgAttrChoose },
0x08: { n:'PtgAttrGoto', f:parse_PtgAttrGoto },
0x10: { n:'PtgAttrSum', f:parse_PtgAttrSum },
0x20: { n:'PtgAttrBaxcel', f:parse_PtgAttrBaxcel },
0x40: { n:'PtgAttrSpace', f:parse_PtgAttrSpace },
0x41: { n:'PtgAttrSpaceSemi', f:parse_PtgAttrSpaceSemi },
0x80: { n:'PtgAttrIfError', f:parse_PtgAttrIfError },
0xFF: {}
};

/* 2.4.127 TODO */
function parse_Formula(blob, length, opts) {
	var end = blob.l + length;
	var cell = parse_XLSCell(blob, 6);
	if(opts.biff == 2) ++blob.l;
	var val = parse_FormulaValue(blob,8);
	var flags = blob.read_shift(1);
	if(opts.biff != 2) {
		blob.read_shift(1);
		if(opts.biff >= 5) {
			var chn = blob.read_shift(4);
		}
	}
	var cbf = parse_XLSCellParsedFormula(blob, end - blob.l, opts);
	return {cell:cell, val:val[0], formula:cbf, shared: (flags >> 3) & 1, tt:val[1]};
}

/* 2.5.133 TODO: how to emit empty strings? */
function parse_FormulaValue(blob) {
	var b;
	if(__readUInt16LE(blob,blob.l + 6) !== 0xFFFF) return [parse_Xnum(blob),'n'];
	switch(blob[blob.l]) {
		case 0x00: blob.l += 8; return ["String", 's'];
		case 0x01: b = blob[blob.l+2] === 0x1; blob.l += 8; return [b,'b'];
		case 0x02: b = blob[blob.l+2]; blob.l += 8; return [b,'e'];
		case 0x03: blob.l += 8; return ["",'s'];
	}
	return [];
}

/* 2.5.198.103 */
function parse_RgbExtra(blob, length, rgce, opts) {
	if(opts.biff < 8) return parsenoop(blob, length);
	var target = blob.l + length;
	var o = [];
	for(var i = 0; i !== rgce.length; ++i) {
		switch(rgce[i][0]) {
			case 'PtgArray': /* PtgArray -> PtgExtraArray */
				rgce[i][1] = parse_PtgExtraArray(blob, 0, opts);
				o.push(rgce[i][1]);
				break;
			case 'PtgMemArea': /* PtgMemArea -> PtgExtraMem */
				rgce[i][2] = parse_PtgExtraMem(blob, rgce[i][1]);
				o.push(rgce[i][2]);
				break;
			case 'PtgExp': /* PtgExp -> PtgExtraCol */
				if(opts && opts.biff == 12) {
					rgce[i][1][1] = blob.read_shift(4);
					o.push(rgce[i][1]);
				} break;
			default: break;
		}
	}
	length = target - blob.l;
	/* note: this is technically an error but Excel disregards */
	//if(target !== blob.l && blob.l !== target - length) throw new Error(target + " != " + blob.l);
	if(length !== 0) o.push(parsenoop(blob, length));
	return o;
}

/* 2.5.198.21 */
function parse_NameParsedFormula(blob, length, opts, cce) {
	var target = blob.l + length;
	var rgce = parse_Rgce(blob, cce, opts);
	var rgcb;
	if(target !== blob.l) rgcb = parse_RgbExtra(blob, target - blob.l, rgce, opts);
	return [rgce, rgcb];
}

/* 2.5.198.3 TODO */
function parse_XLSCellParsedFormula(blob, length, opts) {
	var target = blob.l + length, len = opts.biff == 2 ? 1 : 2;
	var rgcb, cce = blob.read_shift(len); // length of rgce
	if(cce == 0xFFFF) return [[],parsenoop(blob, length-2)];
	var rgce = parse_Rgce(blob, cce, opts);
	if(length !== cce + len) rgcb = parse_RgbExtra(blob, length - cce - len, rgce, opts);
	return [rgce, rgcb];
}

/* 2.5.198.118 TODO */
function parse_SharedParsedFormula(blob, length, opts) {
	var target = blob.l + length;
	var rgcb, cce = blob.read_shift(2); // length of rgce
	var rgce = parse_Rgce(blob, cce, opts);
	if(cce == 0xFFFF) return [[],parsenoop(blob, length-2)];
	if(length !== cce + 2) rgcb = parse_RgbExtra(blob, target - cce - 2, rgce, opts);
	return [rgce, rgcb];
}

/* 2.5.198.1 TODO */
function parse_ArrayParsedFormula(blob, length, opts, ref) {
	var target = blob.l + length, len = opts.biff == 2 ? 1 : 2;
	var rgcb, cce = blob.read_shift(len); // length of rgce
	if(cce == 0xFFFF) return [[],parsenoop(blob, length-2)];
	var rgce = parse_Rgce(blob, cce, opts);
	if(length !== cce + len) rgcb = parse_RgbExtra(blob, length - cce - len, rgce, opts);
	return [rgce, rgcb];
}

/* 2.5.198.104 */
function parse_Rgce(blob, length, opts) {
	var target = blob.l + length;
	var R, id, ptgs = [];
	while(target != blob.l) {
		length = target - blob.l;
		id = blob[blob.l];
		R = PtgTypes[id];
		if(id === 0x18 || id === 0x19) {
			id = blob[blob.l + 1];
			R = (id === 0x18 ? Ptg18 : Ptg19)[id];
		}
		if(!R || !R.f) { /*ptgs.push*/(parsenoop(blob, length)); }
		// $FlowIgnore
		else { ptgs.push([R.n, R.f(blob, length, opts)]); }
	}
	return ptgs;
}

function stringify_array(f) {
	var o = [];
	for(var i = 0; i < f.length; ++i) {
		var x = f[i], r = [];
		for(var j = 0; j < x.length; ++j) {
			var y = x[j];
			if(y) switch(y[0]) {
				// TODO: handle embedded quotes
				case 0x02:
r.push('"' + y[1].replace(/"/g,'""') + '"'); break;
				default: r.push(y[1]);
			} else r.push("");
		}
		o.push(r.join(","));
	}
	return o.join(";");
}

/* [MS-XLS] 2.2.2 TODO */
/* [MS-XLSB] 2.2.2 */
var PtgBinOp = {
	PtgAdd: "+",
	PtgConcat: "&",
	PtgDiv: "/",
	PtgEq: "=",
	PtgGe: ">=",
	PtgGt: ">",
	PtgLe: "<=",
	PtgLt: "<",
	PtgMul: "*",
	PtgNe: "<>",
	PtgPower: "^",
	PtgSub: "-"
};
function stringify_formula(formula/*Array<any>*/, range, cell, supbooks, opts) {
	//console.log(formula);
	var _range = /*range != null ? range :*/ {s:{c:0, r:0},e:{c:0, r:0}};
	var stack = [], e1, e2, type, c, ixti=0, nameidx=0, r, sname="";
	if(!formula[0] || !formula[0][0]) return "";
	var last_sp = -1, sp = "";
	//console.log("--",cell,formula[0])
	for(var ff = 0, fflen = formula[0].length; ff < fflen; ++ff) {
		var f = formula[0][ff];
		//console.log("++",f, stack)
		switch(f[0]) {
			case 'PtgUminus': /* 2.5.198.93 */
				stack.push("-" + stack.pop()); break;
			case 'PtgUplus': /* 2.5.198.95 */
				stack.push("+" + stack.pop()); break;
			case 'PtgPercent': /* 2.5.198.81 */
				stack.push(stack.pop() + "%"); break;

			case 'PtgAdd':    /* 2.5.198.26 */
			case 'PtgConcat': /* 2.5.198.43 */
			case 'PtgDiv':    /* 2.5.198.45 */
			case 'PtgEq':     /* 2.5.198.56 */
			case 'PtgGe':     /* 2.5.198.64 */
			case 'PtgGt':     /* 2.5.198.65 */
			case 'PtgLe':     /* 2.5.198.68 */
			case 'PtgLt':     /* 2.5.198.69 */
			case 'PtgMul':    /* 2.5.198.75 */
			case 'PtgNe':     /* 2.5.198.78 */
			case 'PtgPower':  /* 2.5.198.82 */
			case 'PtgSub':    /* 2.5.198.90 */
				e1 = stack.pop(); e2 = stack.pop();
				if(last_sp >= 0) {
					switch(formula[0][last_sp][1][0]) {
						case 0:
							// $FlowIgnore
							sp = fill(" ", formula[0][last_sp][1][1]); break;
						case 1:
							// $FlowIgnore
							sp = fill("\r", formula[0][last_sp][1][1]); break;
						default:
							sp = "";
							// $FlowIgnore
							if(opts.WTF) throw new Error("Unexpected PtgAttrSpaceType " + formula[0][last_sp][1][0]);
					}
					e2 = e2 + sp;
					last_sp = -1;
				}
				stack.push(e2+PtgBinOp[f[0]]+e1);
				break;

			case 'PtgIsect': /* 2.5.198.67 */
				e1 = stack.pop(); e2 = stack.pop();
				stack.push(e2+" "+e1);
				break;
			case 'PtgUnion': /* 2.5.198.94 */
				e1 = stack.pop(); e2 = stack.pop();
				stack.push(e2+","+e1);
				break;
			case 'PtgRange': /* 2.5.198.83 */
				e1 = stack.pop(); e2 = stack.pop();
				stack.push(e2+":"+e1);
				break;

			case 'PtgAttrChoose': /* 2.5.198.34 */
				break;
			case 'PtgAttrGoto': /* 2.5.198.35 */
				break;
			case 'PtgAttrIf': /* 2.5.198.36 */
				break;
			case 'PtgAttrIfError': /* [MS-XLSB] 2.5.97.28 */
				break;


			case 'PtgRef': /* 2.5.198.84 */
				type = f[1][0]; c = shift_cell_xls((f[1][1]), _range, opts);
				stack.push(encode_cell_xls(c));
				break;
			case 'PtgRefN': /* 2.5.198.88 */
				type = f[1][0]; c = cell ? shift_cell_xls((f[1][1]), cell, opts) : (f[1][1]);
				stack.push(encode_cell_xls(c));
				break;
			case 'PtgRef3d': /* 2.5.198.85 */
				type = f[1][0]; ixti = f[1][1]; c = shift_cell_xls((f[1][2]), _range, opts);
				sname = supbooks.SheetNames[ixti];
				var w = sname; /* IE9 fails on defined names */
				stack.push(sname + "!" + encode_cell_xls(c));
				break;

			case 'PtgFunc': /* 2.5.198.62 */
			case 'PtgFuncVar': /* 2.5.198.63 */
				//console.log(f[1]);
				/* f[1] = [argc, func, type] */
				var argc = f[1][0], func = f[1][1];
				if(!argc) argc = 0;
				var args = argc == 0 ? [] : stack.slice(-argc);
				stack.length -= argc;
				if(func === 'User') func = args.shift();
				stack.push(func + "(" + args.join(",") + ")");
				break;

			case 'PtgBool': /* 2.5.198.42 */
				stack.push(f[1] ? "TRUE" : "FALSE"); break;
			case 'PtgInt': /* 2.5.198.66 */
				stack.push(f[1]); break;
			case 'PtgNum': /* 2.5.198.79 TODO: precision? */
				stack.push(String(f[1])); break;
			case 'PtgStr': /* 2.5.198.89 */
				// $FlowIgnore
				stack.push('"' + f[1] + '"'); break;
			case 'PtgErr': /* 2.5.198.57 */
				stack.push(f[1]); break;
			case 'PtgAreaN': /* 2.5.198.31 TODO */
				type = f[1][0]; r = shift_range_xls(f[1][1], _range, opts);
				stack.push(encode_range_xls((r), opts));
				break;
			case 'PtgArea': /* 2.5.198.27 TODO: fixed points */
				type = f[1][0]; r = shift_range_xls(f[1][1], _range, opts);
				stack.push(encode_range_xls((r), opts));
				break;
			case 'PtgArea3d': /* 2.5.198.28 TODO */
				type = f[1][0]; ixti = f[1][1]; r = f[1][2];
				sname = (supbooks && supbooks[1] ? supbooks[1][ixti+1] : "**MISSING**");
				stack.push(sname + "!" + encode_range((r)));
				break;
			case 'PtgAttrSum': /* 2.5.198.41 */
				stack.push("SUM(" + stack.pop() + ")");
				break;

			case 'PtgAttrSemi': /* 2.5.198.37 */
				break;

			case 'PtgName': /* 2.5.97.60 TODO: revisions */
				/* f[1] = type, 0, nameindex */
				nameidx = (f[1][2]);
				var lbl = (supbooks.names||[])[nameidx-1] || (supbooks[0]||[])[nameidx];
				var name = lbl ? lbl.Name : "**MISSING**" + String(nameidx);
				if(name in XLSXFutureFunctions) name = XLSXFutureFunctions[name];
				stack.push(name);
				break;

			case 'PtgNameX': /* 2.5.97.61 TODO: revisions */
				/* f[1] = type, ixti, nameindex */
				var bookidx = (f[1][1]); nameidx = (f[1][2]); var externbook;
				/* TODO: Properly handle missing values */
				//console.log(bookidx, supbooks);
				if(opts.biff <= 5) {
					if(bookidx < 0) bookidx = -bookidx;
					if(supbooks[bookidx]) externbook = supbooks[bookidx][nameidx];
				} else {
					var pnxname = supbooks.SheetNames[bookidx];
					var o = "";
					if(((supbooks[bookidx]||[])[0]||[])[0] == 0x3A01){/* empty */}
					else if(((supbooks[bookidx]||[])[0]||[])[0] == 0x0401){
						if(supbooks[bookidx][nameidx] && supbooks[bookidx][nameidx].itab > 0) {
							o = supbooks.SheetNames[supbooks[bookidx][nameidx].itab-1] + "!";
						}
					}
					else o = supbooks.SheetNames[nameidx-1]+ "!";
					if(supbooks[bookidx] && supbooks[bookidx][nameidx]) o += supbooks[bookidx][nameidx].Name;
					else if(supbooks[0] && supbooks[0][nameidx]) o += supbooks[0][nameidx].Name;
					else o += "??NAMEX??";
					stack.push(o);
					break;
				}
				if(!externbook) externbook = {Name: "??NAMEX??"};
				stack.push(externbook.Name);
				break;

			case 'PtgParen': /* 2.5.198.80 */
				var lp = '(', rp = ')';
				if(last_sp >= 0) {
					sp = "";
					switch(formula[0][last_sp][1][0]) {
						// $FlowIgnore
						case 2: lp = fill(" ", formula[0][last_sp][1][1]) + lp; break;
						// $FlowIgnore
						case 3: lp = fill("\r", formula[0][last_sp][1][1]) + lp; break;
						// $FlowIgnore
						case 4: rp = fill(" ", formula[0][last_sp][1][1]) + rp; break;
						// $FlowIgnore
						case 5: rp = fill("\r", formula[0][last_sp][1][1]) + rp; break;
						default:
							// $FlowIgnore
							if(opts.WTF) throw new Error("Unexpected PtgAttrSpaceType " + formula[0][last_sp][1][0]);
					}
					last_sp = -1;
				}
				stack.push(lp + stack.pop() + rp); break;

			case 'PtgRefErr': /* 2.5.198.86 */
				stack.push('#REF!'); break;

			case 'PtgRefErr3d': /* 2.5.198.87 */
				stack.push('#REF!'); break;

			case 'PtgExp': /* 2.5.198.58 TODO */
				c = {c:f[1][1],r:f[1][0]};
				var q = ({c: cell.c, r:cell.r});
				if(supbooks.sharedf[encode_cell(c)]) {
					var parsedf = (supbooks.sharedf[encode_cell(c)]);
					stack.push(stringify_formula(parsedf, _range, q, supbooks, opts));
				}
				else {
					var fnd = false;
					for(e1=0;e1!=supbooks.arrayf.length; ++e1) {
						/* TODO: should be something like range_has */
						e2 = supbooks.arrayf[e1];
						if(c.c < e2[0].s.c || c.c > e2[0].e.c) continue;
						if(c.r < e2[0].s.r || c.r > e2[0].e.r) continue;
						stack.push(stringify_formula(e2[1], _range, q, supbooks, opts));
						fnd = true;
						break;
					}
					if(!fnd) stack.push(f[1]);
				}
				break;

			case 'PtgArray': /* 2.5.198.32 TODO */
				stack.push("{" + stringify_array(f[1]) + "}");
				break;

			case 'PtgMemArea': /* 2.5.198.70 TODO: confirm this is a non-display */
				//stack.push("(" + f[2].map(encode_range).join(",") + ")");
				break;

			case 'PtgAttrSpace': /* 2.5.198.38 */
			case 'PtgAttrSpaceSemi': /* 2.5.198.39 */
				last_sp = ff;
				break;

			case 'PtgTbl': /* 2.5.198.92 TODO */
				break;

			case 'PtgMemErr': /* 2.5.198.71 */
				break;

			case 'PtgMissArg': /* 2.5.198.74 */
				stack.push("");
				break;

			case 'PtgAreaErr': /* 2.5.198.29 */
				stack.push("#REF!"); break;

			case 'PtgAreaErr3d': /* 2.5.198.30 */
				stack.push("#REF!"); break;

			case 'PtgMemFunc': /* 2.5.198.72 TODO */
				break;

			default: throw new Error('Unrecognized Formula Token: ' + String(f));
		}
		var PtgNonDisp = ['PtgAttrSpace', 'PtgAttrSpaceSemi', 'PtgAttrGoto'];
		if(last_sp >= 0 && PtgNonDisp.indexOf(formula[0][ff][0]) == -1) {
			f = formula[0][last_sp];
			var _left = true;
			switch(f[1][0]) {
				/* note: some bad XLSB files omit the PtgParen */
				case 4: _left = false;
				/* falls through */
				case 0:
					// $FlowIgnore
					sp = fill(" ", f[1][1]); break;
				case 5: _left = false;
				/* falls through */
				case 1:
					// $FlowIgnore
					sp = fill("\r", f[1][1]); break;
				default:
					sp = "";
					// $FlowIgnore
					if(opts.WTF) throw new Error("Unexpected PtgAttrSpaceType " + f[1][0]);
			}
			stack.push((_left ? sp : "") + stack.pop() + (_left ? "" : sp));
			last_sp = -1;
		}
		//console.log("::",f, stack)
	}
	//console.log("--",stack);
	if(stack.length > 1 && opts.WTF) throw new Error("bad formula stack");
	return stack[0];
}

/* XLSB Parsed Formula records have the same shape */
function parse_XLSBParsedFormula(data, length, opts) {
	var end = data.l + length;
	var cce = data.read_shift(4);
	var rgce = parse_Rgce(data, cce, opts);
	var cb = data.read_shift(4);
	var rgcb = cb > 0 ? parse_RgbExtra(data, cb, rgce, opts) : null;
	return [rgce, rgcb];
}

/* [MS-XLSB] 2.5.97.1 ArrayParsedFormula */
var parse_XLSBArrayParsedFormula = parse_XLSBParsedFormula;
/* [MS-XLSB] 2.5.97.4 CellParsedFormula */
var parse_XLSBCellParsedFormula = parse_XLSBParsedFormula;
/* [MS-XLSB] 2.5.97.12 NameParsedFormula */
var parse_XLSBNameParsedFormula = parse_XLSBParsedFormula;
/* [MS-XLSB] 2.5.97.98 SharedParsedFormula */
var parse_XLSBSharedParsedFormula = parse_XLSBParsedFormula;
/* [MS-XLS] 2.5.198.44 */
var PtgDataType = {
0x1: "REFERENCE", // reference to range
0x2: "VALUE", // single value
0x3: "ARRAY" // array of values
};

/* [MS-XLS] 2.5.198.4 */
var Cetab = {
0x0000: 'BEEP',
0x0001: 'OPEN',
0x0002: 'OPEN.LINKS',
0x0003: 'CLOSE.ALL',
0x0004: 'SAVE',
0x0005: 'SAVE.AS',
0x0006: 'FILE.DELETE',
0x0007: 'PAGE.SETUP',
0x0008: 'PRINT',
0x0009: 'PRINTER.SETUP',
0x000A: 'QUIT',
0x000B: 'NEW.WINDOW',
0x000C: 'ARRANGE.ALL',
0x000D: 'WINDOW.SIZE',
0x000E: 'WINDOW.MOVE',
0x000F: 'FULL',
0x0010: 'CLOSE',
0x0011: 'RUN',
0x0016: 'SET.PRINT.AREA',
0x0017: 'SET.PRINT.TITLES',
0x0018: 'SET.PAGE.BREAK',
0x0019: 'REMOVE.PAGE.BREAK',
0x001A: 'FONT',
0x001B: 'DISPLAY',
0x001C: 'PROTECT.DOCUMENT',
0x001D: 'PRECISION',
0x001E: 'A1.R1C1',
0x001F: 'CALCULATE.NOW',
0x0020: 'CALCULATION',
0x0022: 'DATA.FIND',
0x0023: 'EXTRACT',
0x0024: 'DATA.DELETE',
0x0025: 'SET.DATABASE',
0x0026: 'SET.CRITERIA',
0x0027: 'SORT',
0x0028: 'DATA.SERIES',
0x0029: 'TABLE',
0x002A: 'FORMAT.NUMBER',
0x002B: 'ALIGNMENT',
0x002C: 'STYLE',
0x002D: 'BORDER',
0x002E: 'CELL.PROTECTION',
0x002F: 'COLUMN.WIDTH',
0x0030: 'UNDO',
0x0031: 'CUT',
0x0032: 'COPY',
0x0033: 'PASTE',
0x0034: 'CLEAR',
0x0035: 'PASTE.SPECIAL',
0x0036: 'EDIT.DELETE',
0x0037: 'INSERT',
0x0038: 'FILL.RIGHT',
0x0039: 'FILL.DOWN',
0x003D: 'DEFINE.NAME',
0x003E: 'CREATE.NAMES',
0x003F: 'FORMULA.GOTO',
0x0040: 'FORMULA.FIND',
0x0041: 'SELECT.LAST.CELL',
0x0042: 'SHOW.ACTIVE.CELL',
0x0043: 'GALLERY.AREA',
0x0044: 'GALLERY.BAR',
0x0045: 'GALLERY.COLUMN',
0x0046: 'GALLERY.LINE',
0x0047: 'GALLERY.PIE',
0x0048: 'GALLERY.SCATTER',
0x0049: 'COMBINATION',
0x004A: 'PREFERRED',
0x004B: 'ADD.OVERLAY',
0x004C: 'GRIDLINES',
0x004D: 'SET.PREFERRED',
0x004E: 'AXES',
0x004F: 'LEGEND',
0x0050: 'ATTACH.TEXT',
0x0051: 'ADD.ARROW',
0x0052: 'SELECT.CHART',
0x0053: 'SELECT.PLOT.AREA',
0x0054: 'PATTERNS',
0x0055: 'MAIN.CHART',
0x0056: 'OVERLAY',
0x0057: 'SCALE',
0x0058: 'FORMAT.LEGEND',
0x0059: 'FORMAT.TEXT',
0x005A: 'EDIT.REPEAT',
0x005B: 'PARSE',
0x005C: 'JUSTIFY',
0x005D: 'HIDE',
0x005E: 'UNHIDE',
0x005F: 'WORKSPACE',
0x0060: 'FORMULA',
0x0061: 'FORMULA.FILL',
0x0062: 'FORMULA.ARRAY',
0x0063: 'DATA.FIND.NEXT',
0x0064: 'DATA.FIND.PREV',
0x0065: 'FORMULA.FIND.NEXT',
0x0066: 'FORMULA.FIND.PREV',
0x0067: 'ACTIVATE',
0x0068: 'ACTIVATE.NEXT',
0x0069: 'ACTIVATE.PREV',
0x006A: 'UNLOCKED.NEXT',
0x006B: 'UNLOCKED.PREV',
0x006C: 'COPY.PICTURE',
0x006D: 'SELECT',
0x006E: 'DELETE.NAME',
0x006F: 'DELETE.FORMAT',
0x0070: 'VLINE',
0x0071: 'HLINE',
0x0072: 'VPAGE',
0x0073: 'HPAGE',
0x0074: 'VSCROLL',
0x0075: 'HSCROLL',
0x0076: 'ALERT',
0x0077: 'NEW',
0x0078: 'CANCEL.COPY',
0x0079: 'SHOW.CLIPBOARD',
0x007A: 'MESSAGE',
0x007C: 'PASTE.LINK',
0x007D: 'APP.ACTIVATE',
0x007E: 'DELETE.ARROW',
0x007F: 'ROW.HEIGHT',
0x0080: 'FORMAT.MOVE',
0x0081: 'FORMAT.SIZE',
0x0082: 'FORMULA.REPLACE',
0x0083: 'SEND.KEYS',
0x0084: 'SELECT.SPECIAL',
0x0085: 'APPLY.NAMES',
0x0086: 'REPLACE.FONT',
0x0087: 'FREEZE.PANES',
0x0088: 'SHOW.INFO',
0x0089: 'SPLIT',
0x008A: 'ON.WINDOW',
0x008B: 'ON.DATA',
0x008C: 'DISABLE.INPUT',
0x008E: 'OUTLINE',
0x008F: 'LIST.NAMES',
0x0090: 'FILE.CLOSE',
0x0091: 'SAVE.WORKBOOK',
0x0092: 'DATA.FORM',
0x0093: 'COPY.CHART',
0x0094: 'ON.TIME',
0x0095: 'WAIT',
0x0096: 'FORMAT.FONT',
0x0097: 'FILL.UP',
0x0098: 'FILL.LEFT',
0x0099: 'DELETE.OVERLAY',
0x009B: 'SHORT.MENUS',
0x009F: 'SET.UPDATE.STATUS',
0x00A1: 'COLOR.PALETTE',
0x00A2: 'DELETE.STYLE',
0x00A3: 'WINDOW.RESTORE',
0x00A4: 'WINDOW.MAXIMIZE',
0x00A6: 'CHANGE.LINK',
0x00A7: 'CALCULATE.DOCUMENT',
0x00A8: 'ON.KEY',
0x00A9: 'APP.RESTORE',
0x00AA: 'APP.MOVE',
0x00AB: 'APP.SIZE',
0x00AC: 'APP.MINIMIZE',
0x00AD: 'APP.MAXIMIZE',
0x00AE: 'BRING.TO.FRONT',
0x00AF: 'SEND.TO.BACK',
0x00B9: 'MAIN.CHART.TYPE',
0x00BA: 'OVERLAY.CHART.TYPE',
0x00BB: 'SELECT.END',
0x00BC: 'OPEN.MAIL',
0x00BD: 'SEND.MAIL',
0x00BE: 'STANDARD.FONT',
0x00BF: 'CONSOLIDATE',
0x00C0: 'SORT.SPECIAL',
0x00C1: 'GALLERY.3D.AREA',
0x00C2: 'GALLERY.3D.COLUMN',
0x00C3: 'GALLERY.3D.LINE',
0x00C4: 'GALLERY.3D.PIE',
0x00C5: 'VIEW.3D',
0x00C6: 'GOAL.SEEK',
0x00C7: 'WORKGROUP',
0x00C8: 'FILL.GROUP',
0x00C9: 'UPDATE.LINK',
0x00CA: 'PROMOTE',
0x00CB: 'DEMOTE',
0x00CC: 'SHOW.DETAIL',
0x00CE: 'UNGROUP',
0x00CF: 'OBJECT.PROPERTIES',
0x00D0: 'SAVE.NEW.OBJECT',
0x00D1: 'SHARE',
0x00D2: 'SHARE.NAME',
0x00D3: 'DUPLICATE',
0x00D4: 'APPLY.STYLE',
0x00D5: 'ASSIGN.TO.OBJECT',
0x00D6: 'OBJECT.PROTECTION',
0x00D7: 'HIDE.OBJECT',
0x00D8: 'SET.EXTRACT',
0x00D9: 'CREATE.PUBLISHER',
0x00DA: 'SUBSCRIBE.TO',
0x00DB: 'ATTRIBUTES',
0x00DC: 'SHOW.TOOLBAR',
0x00DE: 'PRINT.PREVIEW',
0x00DF: 'EDIT.COLOR',
0x00E0: 'SHOW.LEVELS',
0x00E1: 'FORMAT.MAIN',
0x00E2: 'FORMAT.OVERLAY',
0x00E3: 'ON.RECALC',
0x00E4: 'EDIT.SERIES',
0x00E5: 'DEFINE.STYLE',
0x00F0: 'LINE.PRINT',
0x00F3: 'ENTER.DATA',
0x00F9: 'GALLERY.RADAR',
0x00FA: 'MERGE.STYLES',
0x00FB: 'EDITION.OPTIONS',
0x00FC: 'PASTE.PICTURE',
0x00FD: 'PASTE.PICTURE.LINK',
0x00FE: 'SPELLING',
0x0100: 'ZOOM',
0x0103: 'INSERT.OBJECT',
0x0104: 'WINDOW.MINIMIZE',
0x0109: 'SOUND.NOTE',
0x010A: 'SOUND.PLAY',
0x010B: 'FORMAT.SHAPE',
0x010C: 'EXTEND.POLYGON',
0x010D: 'FORMAT.AUTO',
0x0110: 'GALLERY.3D.BAR',
0x0111: 'GALLERY.3D.SURFACE',
0x0112: 'FILL.AUTO',
0x0114: 'CUSTOMIZE.TOOLBAR',
0x0115: 'ADD.TOOL',
0x0116: 'EDIT.OBJECT',
0x0117: 'ON.DOUBLECLICK',
0x0118: 'ON.ENTRY',
0x0119: 'WORKBOOK.ADD',
0x011A: 'WORKBOOK.MOVE',
0x011B: 'WORKBOOK.COPY',
0x011C: 'WORKBOOK.OPTIONS',
0x011D: 'SAVE.WORKSPACE',
0x0120: 'CHART.WIZARD',
0x0121: 'DELETE.TOOL',
0x0122: 'MOVE.TOOL',
0x0123: 'WORKBOOK.SELECT',
0x0124: 'WORKBOOK.ACTIVATE',
0x0125: 'ASSIGN.TO.TOOL',
0x0127: 'COPY.TOOL',
0x0128: 'RESET.TOOL',
0x0129: 'CONSTRAIN.NUMERIC',
0x012A: 'PASTE.TOOL',
0x012E: 'WORKBOOK.NEW',
0x0131: 'SCENARIO.CELLS',
0x0132: 'SCENARIO.DELETE',
0x0133: 'SCENARIO.ADD',
0x0134: 'SCENARIO.EDIT',
0x0135: 'SCENARIO.SHOW',
0x0136: 'SCENARIO.SHOW.NEXT',
0x0137: 'SCENARIO.SUMMARY',
0x0138: 'PIVOT.TABLE.WIZARD',
0x0139: 'PIVOT.FIELD.PROPERTIES',
0x013A: 'PIVOT.FIELD',
0x013B: 'PIVOT.ITEM',
0x013C: 'PIVOT.ADD.FIELDS',
0x013E: 'OPTIONS.CALCULATION',
0x013F: 'OPTIONS.EDIT',
0x0140: 'OPTIONS.VIEW',
0x0141: 'ADDIN.MANAGER',
0x0142: 'MENU.EDITOR',
0x0143: 'ATTACH.TOOLBARS',
0x0144: 'VBAActivate',
0x0145: 'OPTIONS.CHART',
0x0148: 'VBA.INSERT.FILE',
0x014A: 'VBA.PROCEDURE.DEFINITION',
0x0150: 'ROUTING.SLIP',
0x0152: 'ROUTE.DOCUMENT',
0x0153: 'MAIL.LOGON',
0x0156: 'INSERT.PICTURE',
0x0157: 'EDIT.TOOL',
0x0158: 'GALLERY.DOUGHNUT',
0x015E: 'CHART.TREND',
0x0160: 'PIVOT.ITEM.PROPERTIES',
0x0162: 'WORKBOOK.INSERT',
0x0163: 'OPTIONS.TRANSITION',
0x0164: 'OPTIONS.GENERAL',
0x0172: 'FILTER.ADVANCED',
0x0175: 'MAIL.ADD.MAILER',
0x0176: 'MAIL.DELETE.MAILER',
0x0177: 'MAIL.REPLY',
0x0178: 'MAIL.REPLY.ALL',
0x0179: 'MAIL.FORWARD',
0x017A: 'MAIL.NEXT.LETTER',
0x017B: 'DATA.LABEL',
0x017C: 'INSERT.TITLE',
0x017D: 'FONT.PROPERTIES',
0x017E: 'MACRO.OPTIONS',
0x017F: 'WORKBOOK.HIDE',
0x0180: 'WORKBOOK.UNHIDE',
0x0181: 'WORKBOOK.DELETE',
0x0182: 'WORKBOOK.NAME',
0x0184: 'GALLERY.CUSTOM',
0x0186: 'ADD.CHART.AUTOFORMAT',
0x0187: 'DELETE.CHART.AUTOFORMAT',
0x0188: 'CHART.ADD.DATA',
0x0189: 'AUTO.OUTLINE',
0x018A: 'TAB.ORDER',
0x018B: 'SHOW.DIALOG',
0x018C: 'SELECT.ALL',
0x018D: 'UNGROUP.SHEETS',
0x018E: 'SUBTOTAL.CREATE',
0x018F: 'SUBTOTAL.REMOVE',
0x0190: 'RENAME.OBJECT',
0x019C: 'WORKBOOK.SCROLL',
0x019D: 'WORKBOOK.NEXT',
0x019E: 'WORKBOOK.PREV',
0x019F: 'WORKBOOK.TAB.SPLIT',
0x01A0: 'FULL.SCREEN',
0x01A1: 'WORKBOOK.PROTECT',
0x01A4: 'SCROLLBAR.PROPERTIES',
0x01A5: 'PIVOT.SHOW.PAGES',
0x01A6: 'TEXT.TO.COLUMNS',
0x01A7: 'FORMAT.CHARTTYPE',
0x01A8: 'LINK.FORMAT',
0x01A9: 'TRACER.DISPLAY',
0x01AE: 'TRACER.NAVIGATE',
0x01AF: 'TRACER.CLEAR',
0x01B0: 'TRACER.ERROR',
0x01B1: 'PIVOT.FIELD.GROUP',
0x01B2: 'PIVOT.FIELD.UNGROUP',
0x01B3: 'CHECKBOX.PROPERTIES',
0x01B4: 'LABEL.PROPERTIES',
0x01B5: 'LISTBOX.PROPERTIES',
0x01B6: 'EDITBOX.PROPERTIES',
0x01B7: 'PIVOT.REFRESH',
0x01B8: 'LINK.COMBO',
0x01B9: 'OPEN.TEXT',
0x01BA: 'HIDE.DIALOG',
0x01BB: 'SET.DIALOG.FOCUS',
0x01BC: 'ENABLE.OBJECT',
0x01BD: 'PUSHBUTTON.PROPERTIES',
0x01BE: 'SET.DIALOG.DEFAULT',
0x01BF: 'FILTER',
0x01C0: 'FILTER.SHOW.ALL',
0x01C1: 'CLEAR.OUTLINE',
0x01C2: 'FUNCTION.WIZARD',
0x01C3: 'ADD.LIST.ITEM',
0x01C4: 'SET.LIST.ITEM',
0x01C5: 'REMOVE.LIST.ITEM',
0x01C6: 'SELECT.LIST.ITEM',
0x01C7: 'SET.CONTROL.VALUE',
0x01C8: 'SAVE.COPY.AS',
0x01CA: 'OPTIONS.LISTS.ADD',
0x01CB: 'OPTIONS.LISTS.DELETE',
0x01CC: 'SERIES.AXES',
0x01CD: 'SERIES.X',
0x01CE: 'SERIES.Y',
0x01CF: 'ERRORBAR.X',
0x01D0: 'ERRORBAR.Y',
0x01D1: 'FORMAT.CHART',
0x01D2: 'SERIES.ORDER',
0x01D3: 'MAIL.LOGOFF',
0x01D4: 'CLEAR.ROUTING.SLIP',
0x01D5: 'APP.ACTIVATE.MICROSOFT',
0x01D6: 'MAIL.EDIT.MAILER',
0x01D7: 'ON.SHEET',
0x01D8: 'STANDARD.WIDTH',
0x01D9: 'SCENARIO.MERGE',
0x01DA: 'SUMMARY.INFO',
0x01DB: 'FIND.FILE',
0x01DC: 'ACTIVE.CELL.FONT',
0x01DD: 'ENABLE.TIPWIZARD',
0x01DE: 'VBA.MAKE.ADDIN',
0x01E0: 'INSERTDATATABLE',
0x01E1: 'WORKGROUP.OPTIONS',
0x01E2: 'MAIL.SEND.MAILER',
0x01E5: 'AUTOCORRECT',
0x01E9: 'POST.DOCUMENT',
0x01EB: 'PICKLIST',
0x01ED: 'VIEW.SHOW',
0x01EE: 'VIEW.DEFINE',
0x01EF: 'VIEW.DELETE',
0x01FD: 'SHEET.BACKGROUND',
0x01FE: 'INSERT.MAP.OBJECT',
0x01FF: 'OPTIONS.MENONO',
0x0205: 'MSOCHECKS',
0x0206: 'NORMAL',
0x0207: 'LAYOUT',
0x0208: 'RM.PRINT.AREA',
0x0209: 'CLEAR.PRINT.AREA',
0x020A: 'ADD.PRINT.AREA',
0x020B: 'MOVE.BRK',
0x0221: 'HIDECURR.NOTE',
0x0222: 'HIDEALL.NOTES',
0x0223: 'DELETE.NOTE',
0x0224: 'TRAVERSE.NOTES',
0x0225: 'ACTIVATE.NOTES',
0x026C: 'PROTECT.REVISIONS',
0x026D: 'UNPROTECT.REVISIONS',
0x0287: 'OPTIONS.ME',
0x028D: 'WEB.PUBLISH',
0x029B: 'NEWWEBQUERY',
0x02A1: 'PIVOT.TABLE.CHART',
0x02F1: 'OPTIONS.SAVE',
0x02F3: 'OPTIONS.SPELL',
0x0328: 'HIDEALL.INKANNOTS'
};

/* [MS-XLS] 2.5.198.17 */
/* [MS-XLSB] 2.5.97.10 */
var Ftab = {
0x0000: 'COUNT',
0x0001: 'IF',
0x0002: 'ISNA',
0x0003: 'ISERROR',
0x0004: 'SUM',
0x0005: 'AVERAGE',
0x0006: 'MIN',
0x0007: 'MAX',
0x0008: 'ROW',
0x0009: 'COLUMN',
0x000A: 'NA',
0x000B: 'NPV',
0x000C: 'STDEV',
0x000D: 'DOLLAR',
0x000E: 'FIXED',
0x000F: 'SIN',
0x0010: 'COS',
0x0011: 'TAN',
0x0012: 'ATAN',
0x0013: 'PI',
0x0014: 'SQRT',
0x0015: 'EXP',
0x0016: 'LN',
0x0017: 'LOG10',
0x0018: 'ABS',
0x0019: 'INT',
0x001A: 'SIGN',
0x001B: 'ROUND',
0x001C: 'LOOKUP',
0x001D: 'INDEX',
0x001E: 'REPT',
0x001F: 'MID',
0x0020: 'LEN',
0x0021: 'VALUE',
0x0022: 'TRUE',
0x0023: 'FALSE',
0x0024: 'AND',
0x0025: 'OR',
0x0026: 'NOT',
0x0027: 'MOD',
0x0028: 'DCOUNT',
0x0029: 'DSUM',
0x002A: 'DAVERAGE',
0x002B: 'DMIN',
0x002C: 'DMAX',
0x002D: 'DSTDEV',
0x002E: 'VAR',
0x002F: 'DVAR',
0x0030: 'TEXT',
0x0031: 'LINEST',
0x0032: 'TREND',
0x0033: 'LOGEST',
0x0034: 'GROWTH',
0x0035: 'GOTO',
0x0036: 'HALT',
0x0037: 'RETURN',
0x0038: 'PV',
0x0039: 'FV',
0x003A: 'NPER',
0x003B: 'PMT',
0x003C: 'RATE',
0x003D: 'MIRR',
0x003E: 'IRR',
0x003F: 'RAND',
0x0040: 'MATCH',
0x0041: 'DATE',
0x0042: 'TIME',
0x0043: 'DAY',
0x0044: 'MONTH',
0x0045: 'YEAR',
0x0046: 'WEEKDAY',
0x0047: 'HOUR',
0x0048: 'MINUTE',
0x0049: 'SECOND',
0x004A: 'NOW',
0x004B: 'AREAS',
0x004C: 'ROWS',
0x004D: 'COLUMNS',
0x004E: 'OFFSET',
0x004F: 'ABSREF',
0x0050: 'RELREF',
0x0051: 'ARGUMENT',
0x0052: 'SEARCH',
0x0053: 'TRANSPOSE',
0x0054: 'ERROR',
0x0055: 'STEP',
0x0056: 'TYPE',
0x0057: 'ECHO',
0x0058: 'SET.NAME',
0x0059: 'CALLER',
0x005A: 'DEREF',
0x005B: 'WINDOWS',
0x005C: 'SERIES',
0x005D: 'DOCUMENTS',
0x005E: 'ACTIVE.CELL',
0x005F: 'SELECTION',
0x0060: 'RESULT',
0x0061: 'ATAN2',
0x0062: 'ASIN',
0x0063: 'ACOS',
0x0064: 'CHOOSE',
0x0065: 'HLOOKUP',
0x0066: 'VLOOKUP',
0x0067: 'LINKS',
0x0068: 'INPUT',
0x0069: 'ISREF',
0x006A: 'GET.FORMULA',
0x006B: 'GET.NAME',
0x006C: 'SET.VALUE',
0x006D: 'LOG',
0x006E: 'EXEC',
0x006F: 'CHAR',
0x0070: 'LOWER',
0x0071: 'UPPER',
0x0072: 'PROPER',
0x0073: 'LEFT',
0x0074: 'RIGHT',
0x0075: 'EXACT',
0x0076: 'TRIM',
0x0077: 'REPLACE',
0x0078: 'SUBSTITUTE',
0x0079: 'CODE',
0x007A: 'NAMES',
0x007B: 'DIRECTORY',
0x007C: 'FIND',
0x007D: 'CELL',
0x007E: 'ISERR',
0x007F: 'ISTEXT',
0x0080: 'ISNUMBER',
0x0081: 'ISBLANK',
0x0082: 'T',
0x0083: 'N',
0x0084: 'FOPEN',
0x0085: 'FCLOSE',
0x0086: 'FSIZE',
0x0087: 'FREADLN',
0x0088: 'FREAD',
0x0089: 'FWRITELN',
0x008A: 'FWRITE',
0x008B: 'FPOS',
0x008C: 'DATEVALUE',
0x008D: 'TIMEVALUE',
0x008E: 'SLN',
0x008F: 'SYD',
0x0090: 'DDB',
0x0091: 'GET.DEF',
0x0092: 'REFTEXT',
0x0093: 'TEXTREF',
0x0094: 'INDIRECT',
0x0095: 'REGISTER',
0x0096: 'CALL',
0x0097: 'ADD.BAR',
0x0098: 'ADD.MENU',
0x0099: 'ADD.COMMAND',
0x009A: 'ENABLE.COMMAND',
0x009B: 'CHECK.COMMAND',
0x009C: 'RENAME.COMMAND',
0x009D: 'SHOW.BAR',
0x009E: 'DELETE.MENU',
0x009F: 'DELETE.COMMAND',
0x00A0: 'GET.CHART.ITEM',
0x00A1: 'DIALOG.BOX',
0x00A2: 'CLEAN',
0x00A3: 'MDETERM',
0x00A4: 'MINVERSE',
0x00A5: 'MMULT',
0x00A6: 'FILES',
0x00A7: 'IPMT',
0x00A8: 'PPMT',
0x00A9: 'COUNTA',
0x00AA: 'CANCEL.KEY',
0x00AB: 'FOR',
0x00AC: 'WHILE',
0x00AD: 'BREAK',
0x00AE: 'NEXT',
0x00AF: 'INITIATE',
0x00B0: 'REQUEST',
0x00B1: 'POKE',
0x00B2: 'EXECUTE',
0x00B3: 'TERMINATE',
0x00B4: 'RESTART',
0x00B5: 'HELP',
0x00B6: 'GET.BAR',
0x00B7: 'PRODUCT',
0x00B8: 'FACT',
0x00B9: 'GET.CELL',
0x00BA: 'GET.WORKSPACE',
0x00BB: 'GET.WINDOW',
0x00BC: 'GET.DOCUMENT',
0x00BD: 'DPRODUCT',
0x00BE: 'ISNONTEXT',
0x00BF: 'GET.NOTE',
0x00C0: 'NOTE',
0x00C1: 'STDEVP',
0x00C2: 'VARP',
0x00C3: 'DSTDEVP',
0x00C4: 'DVARP',
0x00C5: 'TRUNC',
0x00C6: 'ISLOGICAL',
0x00C7: 'DCOUNTA',
0x00C8: 'DELETE.BAR',
0x00C9: 'UNREGISTER',
0x00CC: 'USDOLLAR',
0x00CD: 'FINDB',
0x00CE: 'SEARCHB',
0x00CF: 'REPLACEB',
0x00D0: 'LEFTB',
0x00D1: 'RIGHTB',
0x00D2: 'MIDB',
0x00D3: 'LENB',
0x00D4: 'ROUNDUP',
0x00D5: 'ROUNDDOWN',
0x00D6: 'ASC',
0x00D7: 'DBCS',
0x00D8: 'RANK',
0x00DB: 'ADDRESS',
0x00DC: 'DAYS360',
0x00DD: 'TODAY',
0x00DE: 'VDB',
0x00DF: 'ELSE',
0x00E0: 'ELSE.IF',
0x00E1: 'END.IF',
0x00E2: 'FOR.CELL',
0x00E3: 'MEDIAN',
0x00E4: 'SUMPRODUCT',
0x00E5: 'SINH',
0x00E6: 'COSH',
0x00E7: 'TANH',
0x00E8: 'ASINH',
0x00E9: 'ACOSH',
0x00EA: 'ATANH',
0x00EB: 'DGET',
0x00EC: 'CREATE.OBJECT',
0x00ED: 'VOLATILE',
0x00EE: 'LAST.ERROR',
0x00EF: 'CUSTOM.UNDO',
0x00F0: 'CUSTOM.REPEAT',
0x00F1: 'FORMULA.CONVERT',
0x00F2: 'GET.LINK.INFO',
0x00F3: 'TEXT.BOX',
0x00F4: 'INFO',
0x00F5: 'GROUP',
0x00F6: 'GET.OBJECT',
0x00F7: 'DB',
0x00F8: 'PAUSE',
0x00FB: 'RESUME',
0x00FC: 'FREQUENCY',
0x00FD: 'ADD.TOOLBAR',
0x00FE: 'DELETE.TOOLBAR',
0x00FF: 'User',
0x0100: 'RESET.TOOLBAR',
0x0101: 'EVALUATE',
0x0102: 'GET.TOOLBAR',
0x0103: 'GET.TOOL',
0x0104: 'SPELLING.CHECK',
0x0105: 'ERROR.TYPE',
0x0106: 'APP.TITLE',
0x0107: 'WINDOW.TITLE',
0x0108: 'SAVE.TOOLBAR',
0x0109: 'ENABLE.TOOL',
0x010A: 'PRESS.TOOL',
0x010B: 'REGISTER.ID',
0x010C: 'GET.WORKBOOK',
0x010D: 'AVEDEV',
0x010E: 'BETADIST',
0x010F: 'GAMMALN',
0x0110: 'BETAINV',
0x0111: 'BINOMDIST',
0x0112: 'CHIDIST',
0x0113: 'CHIINV',
0x0114: 'COMBIN',
0x0115: 'CONFIDENCE',
0x0116: 'CRITBINOM',
0x0117: 'EVEN',
0x0118: 'EXPONDIST',
0x0119: 'FDIST',
0x011A: 'FINV',
0x011B: 'FISHER',
0x011C: 'FISHERINV',
0x011D: 'FLOOR',
0x011E: 'GAMMADIST',
0x011F: 'GAMMAINV',
0x0120: 'CEILING',
0x0121: 'HYPGEOMDIST',
0x0122: 'LOGNORMDIST',
0x0123: 'LOGINV',
0x0124: 'NEGBINOMDIST',
0x0125: 'NORMDIST',
0x0126: 'NORMSDIST',
0x0127: 'NORMINV',
0x0128: 'NORMSINV',
0x0129: 'STANDARDIZE',
0x012A: 'ODD',
0x012B: 'PERMUT',
0x012C: 'POISSON',
0x012D: 'TDIST',
0x012E: 'WEIBULL',
0x012F: 'SUMXMY2',
0x0130: 'SUMX2MY2',
0x0131: 'SUMX2PY2',
0x0132: 'CHITEST',
0x0133: 'CORREL',
0x0134: 'COVAR',
0x0135: 'FORECAST',
0x0136: 'FTEST',
0x0137: 'INTERCEPT',
0x0138: 'PEARSON',
0x0139: 'RSQ',
0x013A: 'STEYX',
0x013B: 'SLOPE',
0x013C: 'TTEST',
0x013D: 'PROB',
0x013E: 'DEVSQ',
0x013F: 'GEOMEAN',
0x0140: 'HARMEAN',
0x0141: 'SUMSQ',
0x0142: 'KURT',
0x0143: 'SKEW',
0x0144: 'ZTEST',
0x0145: 'LARGE',
0x0146: 'SMALL',
0x0147: 'QUARTILE',
0x0148: 'PERCENTILE',
0x0149: 'PERCENTRANK',
0x014A: 'MODE',
0x014B: 'TRIMMEAN',
0x014C: 'TINV',
0x014E: 'MOVIE.COMMAND',
0x014F: 'GET.MOVIE',
0x0150: 'CONCATENATE',
0x0151: 'POWER',
0x0152: 'PIVOT.ADD.DATA',
0x0153: 'GET.PIVOT.TABLE',
0x0154: 'GET.PIVOT.FIELD',
0x0155: 'GET.PIVOT.ITEM',
0x0156: 'RADIANS',
0x0157: 'DEGREES',
0x0158: 'SUBTOTAL',
0x0159: 'SUMIF',
0x015A: 'COUNTIF',
0x015B: 'COUNTBLANK',
0x015C: 'SCENARIO.GET',
0x015D: 'OPTIONS.LISTS.GET',
0x015E: 'ISPMT',
0x015F: 'DATEDIF',
0x0160: 'DATESTRING',
0x0161: 'NUMBERSTRING',
0x0162: 'ROMAN',
0x0163: 'OPEN.DIALOG',
0x0164: 'SAVE.DIALOG',
0x0165: 'VIEW.GET',
0x0166: 'GETPIVOTDATA',
0x0167: 'HYPERLINK',
0x0168: 'PHONETIC',
0x0169: 'AVERAGEA',
0x016A: 'MAXA',
0x016B: 'MINA',
0x016C: 'STDEVPA',
0x016D: 'VARPA',
0x016E: 'STDEVA',
0x016F: 'VARA',
0x0170: 'BAHTTEXT',
0x0171: 'THAIDAYOFWEEK',
0x0172: 'THAIDIGIT',
0x0173: 'THAIMONTHOFYEAR',
0x0174: 'THAINUMSOUND',
0x0175: 'THAINUMSTRING',
0x0176: 'THAISTRINGLENGTH',
0x0177: 'ISTHAIDIGIT',
0x0178: 'ROUNDBAHTDOWN',
0x0179: 'ROUNDBAHTUP',
0x017A: 'THAIYEAR',
0x017B: 'RTD',

0x017C: 'CUBEVALUE',
0x017D: 'CUBEMEMBER',
0x017E: 'CUBEMEMBERPROPERTY',
0x017F: 'CUBERANKEDMEMBER',
0x0180: 'HEX2BIN',
0x0181: 'HEX2DEC',
0x0182: 'HEX2OCT',
0x0183: 'DEC2BIN',
0x0184: 'DEC2HEX',
0x0185: 'DEC2OCT',
0x0186: 'OCT2BIN',
0x0187: 'OCT2HEX',
0x0188: 'OCT2DEC',
0x0189: 'BIN2DEC',
0x018A: 'BIN2OCT',
0x018B: 'BIN2HEX',
0x018C: 'IMSUB',
0x018D: 'IMDIV',
0x018E: 'IMPOWER',
0x018F: 'IMABS',
0x0190: 'IMSQRT',
0x0191: 'IMLN',
0x0192: 'IMLOG2',
0x0193: 'IMLOG10',
0x0194: 'IMSIN',
0x0195: 'IMCOS',
0x0196: 'IMEXP',
0x0197: 'IMARGUMENT',
0x0198: 'IMCONJUGATE',
0x0199: 'IMAGINARY',
0x019A: 'IMREAL',
0x019B: 'COMPLEX',
0x019C: 'IMSUM',
0x019D: 'IMPRODUCT',
0x019E: 'SERIESSUM',
0x019F: 'FACTDOUBLE',
0x01A0: 'SQRTPI',
0x01A1: 'QUOTIENT',
0x01A2: 'DELTA',
0x01A3: 'GESTEP',
0x01A4: 'ISEVEN',
0x01A5: 'ISODD',
0x01A6: 'MROUND',
0x01A7: 'ERF',
0x01A8: 'ERFC',
0x01A9: 'BESSELJ',
0x01AA: 'BESSELK',
0x01AB: 'BESSELY',
0x01AC: 'BESSELI',
0x01AD: 'XIRR',
0x01AE: 'XNPV',
0x01AF: 'PRICEMAT',
0x01B0: 'YIELDMAT',
0x01B1: 'INTRATE',
0x01B2: 'RECEIVED',
0x01B3: 'DISC',
0x01B4: 'PRICEDISC',
0x01B5: 'YIELDDISC',
0x01B6: 'TBILLEQ',
0x01B7: 'TBILLPRICE',
0x01B8: 'TBILLYIELD',
0x01B9: 'PRICE',
0x01BA: 'YIELD',
0x01BB: 'DOLLARDE',
0x01BC: 'DOLLARFR',
0x01BD: 'NOMINAL',
0x01BE: 'EFFECT',
0x01BF: 'CUMPRINC',
0x01C0: 'CUMIPMT',
0x01C1: 'EDATE',
0x01C2: 'EOMONTH',
0x01C3: 'YEARFRAC',
0x01C4: 'COUPDAYBS',
0x01C5: 'COUPDAYS',
0x01C6: 'COUPDAYSNC',
0x01C7: 'COUPNCD',
0x01C8: 'COUPNUM',
0x01C9: 'COUPPCD',
0x01CA: 'DURATION',
0x01CB: 'MDURATION',
0x01CC: 'ODDLPRICE',
0x01CD: 'ODDLYIELD',
0x01CE: 'ODDFPRICE',
0x01CF: 'ODDFYIELD',
0x01D0: 'RANDBETWEEN',
0x01D1: 'WEEKNUM',
0x01D2: 'AMORDEGRC',
0x01D3: 'AMORLINC',
0x01D4: 'CONVERT',
0x02D4: 'SHEETJS',
0x01D5: 'ACCRINT',
0x01D6: 'ACCRINTM',
0x01D7: 'WORKDAY',
0x01D8: 'NETWORKDAYS',
0x01D9: 'GCD',
0x01DA: 'MULTINOMIAL',
0x01DB: 'LCM',
0x01DC: 'FVSCHEDULE',
0x01DD: 'CUBEKPIMEMBER',
0x01DE: 'CUBESET',
0x01DF: 'CUBESETCOUNT',
0x01E0: 'IFERROR',
0x01E1: 'COUNTIFS',
0x01E2: 'SUMIFS',
0x01E3: 'AVERAGEIF',
0x01E4: 'AVERAGEIFS'
};
var FtabArgc = {
0x0002: 1, /* ISNA */
0x0003: 1, /* ISERROR */
0x000F: 1, /* SIN */
0x0010: 1, /* COS */
0x0011: 1, /* TAN */
0x0012: 1, /* ATAN */
0x0013: 0, /* PI */
0x0014: 1, /* SQRT */
0x0015: 1, /* EXP */
0x0016: 1, /* LN */
0x0017: 1, /* LOG10 */
0x0018: 1, /* ABS */
0x0019: 1, /* INT */
0x001A: 1, /* SIGN */
0x001B: 2, /* ROUND */
0x001E: 2, /* REPT */
0x001F: 3, /* MID */
0x0020: 1, /* LEN */
0x0021: 1, /* VALUE */
0x0026: 1, /* NOT */
0x0027: 2, /* MOD */
0x0028: 3, /* DCOUNT */
0x0029: 3, /* DSUM */
0x002A: 3, /* DAVERAGE */
0x002B: 3, /* DMIN */
0x002C: 3, /* DMAX */
0x002D: 3, /* DSTDEV */
0x002F: 3, /* DVAR */
0x0030: 2, /* TEXT */
0x0035: 1, /* GOTO */
0x003D: 3, /* MIRR */
0x0041: 3, /* DATE */
0x0042: 3, /* TIME */
0x0043: 1, /* DAY */
0x0044: 1, /* MONTH */
0x0045: 1, /* YEAR */
0x0046: 1, /* WEEKDAY */
0x0047: 1, /* HOUR */
0x0048: 1, /* MINUTE */
0x0049: 1, /* SECOND */
0x004B: 1, /* AREAS */
0x004C: 1, /* ROWS */
0x004D: 1, /* COLUMNS */
0x004F: 2, /* ABSREF */
0x0050: 2, /* RELREF */
0x0053: 1, /* TRANSPOSE */
0x0055: 0, /* STEP */
0x0056: 1, /* TYPE */
0x005A: 1, /* DEREF */
0x0061: 2, /* ATAN2 */
0x0062: 1, /* ASIN */
0x0063: 1, /* ACOS */
0x0065: 3, /* HLOOKUP */
0x0066: 3, /* VLOOKUP */
0x0069: 1, /* ISREF */
0x006F: 1, /* CHAR */
0x0070: 1, /* LOWER */
0x0071: 1, /* UPPER */
0x0072: 1, /* PROPER */
0x0075: 2, /* EXACT */
0x0076: 1, /* TRIM */
0x0077: 4, /* REPLACE */
0x0079: 1, /* CODE */
0x007E: 1, /* ISERR */
0x007F: 1, /* ISTEXT */
0x0080: 1, /* ISNUMBER */
0x0081: 1, /* ISBLANK */
0x0082: 1, /* T */
0x0083: 1, /* N */
0x0085: 1, /* FCLOSE */
0x0086: 1, /* FSIZE */
0x0087: 1, /* FREADLN */
0x0088: 2, /* FREAD */
0x0089: 2, /* FWRITELN */
0x008A: 2, /* FWRITE */
0x008C: 1, /* DATEVALUE */
0x008D: 1, /* TIMEVALUE */
0x008E: 3, /* SLN */
0x008F: 4, /* SYD */
0x0090: 4, /* DDB */
0x00A2: 1, /* CLEAN */
0x00A3: 1, /* MDETERM */
0x00A4: 1, /* MINVERSE */
0x00A5: 2, /* MMULT */
0x00AC: 1, /* WHILE */
0x00AF: 2, /* INITIATE */
0x00B0: 2, /* REQUEST */
0x00B1: 3, /* POKE */
0x00B2: 2, /* EXECUTE */
0x00B3: 1, /* TERMINATE */
0x00B8: 1, /* FACT */
0x00BD: 3, /* DPRODUCT */
0x00BE: 1, /* ISNONTEXT */
0x00C3: 3, /* DSTDEVP */
0x00C4: 3, /* DVARP */
0x00C5: 1, /* TRUNC */
0x00C6: 1, /* ISLOGICAL */
0x00C7: 3, /* DCOUNTA */
0x00C9: 1, /* UNREGISTER */
0x00CF: 4, /* REPLACEB */
0x00D2: 3, /* MIDB */
0x00D3: 1, /* LENB */
0x00D4: 2, /* ROUNDUP */
0x00D5: 2, /* ROUNDDOWN */
0x00D6: 1, /* ASC */
0x00D7: 1, /* DBCS */
0x00E5: 1, /* SINH */
0x00E6: 1, /* COSH */
0x00E7: 1, /* TANH */
0x00E8: 1, /* ASINH */
0x00E9: 1, /* ACOSH */
0x00EA: 1, /* ATANH */
0x00EB: 3, /* DGET */
0x00F4: 1, /* INFO */
0x00F7: 4, /* DB */
0x00FC: 2, /* FREQUENCY */
0x0101: 1, /* EVALUATE */
0x0105: 1, /* ERROR.TYPE */
0x010F: 1, /* GAMMALN */
0x0111: 4, /* BINOMDIST */
0x0112: 2, /* CHIDIST */
0x0113: 2, /* CHIINV */
0x0114: 2, /* COMBIN */
0x0115: 3, /* CONFIDENCE */
0x0116: 3, /* CRITBINOM */
0x0117: 1, /* EVEN */
0x0118: 3, /* EXPONDIST */
0x0119: 3, /* FDIST */
0x011A: 3, /* FINV */
0x011B: 1, /* FISHER */
0x011C: 1, /* FISHERINV */
0x011D: 2, /* FLOOR */
0x011E: 4, /* GAMMADIST */
0x011F: 3, /* GAMMAINV */
0x0120: 2, /* CEILING */
0x0121: 4, /* HYPGEOMDIST */
0x0122: 3, /* LOGNORMDIST */
0x0123: 3, /* LOGINV */
0x0124: 3, /* NEGBINOMDIST */
0x0125: 4, /* NORMDIST */
0x0126: 1, /* NORMSDIST */
0x0127: 3, /* NORMINV */
0x0128: 1, /* NORMSINV */
0x0129: 3, /* STANDARDIZE */
0x012A: 1, /* ODD */
0x012B: 2, /* PERMUT */
0x012C: 3, /* POISSON */
0x012D: 3, /* TDIST */
0x012E: 4, /* WEIBULL */
0x012F: 2, /* SUMXMY2 */
0x0130: 2, /* SUMX2MY2 */
0x0131: 2, /* SUMX2PY2 */
0x0132: 2, /* CHITEST */
0x0133: 2, /* CORREL */
0x0134: 2, /* COVAR */
0x0135: 3, /* FORECAST */
0x0136: 2, /* FTEST */
0x0137: 2, /* INTERCEPT */
0x0138: 2, /* PEARSON */
0x0139: 2, /* RSQ */
0x013A: 2, /* STEYX */
0x013B: 2, /* SLOPE */
0x013C: 4, /* TTEST */
0x0145: 2, /* LARGE */
0x0146: 2, /* SMALL */
0x0147: 2, /* QUARTILE */
0x0148: 2, /* PERCENTILE */
0x014B: 2, /* TRIMMEAN */
0x014C: 2, /* TINV */
0x0151: 2, /* POWER */
0x0156: 1, /* RADIANS */
0x0157: 1, /* DEGREES */
0x015A: 2, /* COUNTIF */
0x015B: 1, /* COUNTBLANK */
0x015E: 4, /* ISPMT */
0x015F: 3, /* DATEDIF */
0x0160: 1, /* DATESTRING */
0x0161: 2, /* NUMBERSTRING */
0x0168: 1, /* PHONETIC */
0x0170: 1, /* BAHTTEXT */
0x0171: 1, /* THAIDAYOFWEEK */
0x0172: 1, /* THAIDIGIT */
0x0173: 1, /* THAIMONTHOFYEAR */
0x0174: 1, /* THAINUMSOUND */
0x0175: 1, /* THAINUMSTRING */
0x0176: 1, /* THAISTRINGLENGTH */
0x0177: 1, /* ISTHAIDIGIT */
0x0178: 1, /* ROUNDBAHTDOWN */
0x0179: 1, /* ROUNDBAHTUP */
0x017A: 1, /* THAIYEAR */
0x017E: 3, /* CUBEMEMBERPROPERTY */
0x0181: 1, /* HEX2DEC */
0x0188: 1, /* OCT2DEC */
0x0189: 1, /* BIN2DEC */
0x018C: 2, /* IMSUB */
0x018D: 2, /* IMDIV */
0x018E: 2, /* IMPOWER */
0x018F: 1, /* IMABS */
0x0190: 1, /* IMSQRT */
0x0191: 1, /* IMLN */
0x0192: 1, /* IMLOG2 */
0x0193: 1, /* IMLOG10 */
0x0194: 1, /* IMSIN */
0x0195: 1, /* IMCOS */
0x0196: 1, /* IMEXP */
0x0197: 1, /* IMARGUMENT */
0x0198: 1, /* IMCONJUGATE */
0x0199: 1, /* IMAGINARY */
0x019A: 1, /* IMREAL */
0x019E: 4, /* SERIESSUM */
0x019F: 1, /* FACTDOUBLE */
0x01A0: 1, /* SQRTPI */
0x01A1: 2, /* QUOTIENT */
0x01A4: 1, /* ISEVEN */
0x01A5: 1, /* ISODD */
0x01A6: 2, /* MROUND */
0x01A8: 1, /* ERFC */
0x01A9: 2, /* BESSELJ */
0x01AA: 2, /* BESSELK */
0x01AB: 2, /* BESSELY */
0x01AC: 2, /* BESSELI */
0x01AE: 3, /* XNPV */
0x01B6: 3, /* TBILLEQ */
0x01B7: 3, /* TBILLPRICE */
0x01B8: 3, /* TBILLYIELD */
0x01BB: 2, /* DOLLARDE */
0x01BC: 2, /* DOLLARFR */
0x01BD: 2, /* NOMINAL */
0x01BE: 2, /* EFFECT */
0x01BF: 6, /* CUMPRINC */
0x01C0: 6, /* CUMIPMT */
0x01C1: 2, /* EDATE */
0x01C2: 2, /* EOMONTH */
0x01D0: 2, /* RANDBETWEEN */
0x01D4: 3, /* CONVERT */
0x01DC: 2, /* FVSCHEDULE */
0x01DF: 1, /* CUBESETCOUNT */
0x01E0: 2, /* IFERROR */
0xFFFF: 0
};
/* [MS-XLSX] 2.2.3 Functions */
/* [MS-XLSB] 2.5.97.10 Ftab */
var XLSXFutureFunctions = {
	"_xlfn.ACOT": "ACOT",
	"_xlfn.ACOTH": "ACOTH",
	"_xlfn.AGGREGATE": "AGGREGATE",
	"_xlfn.ARABIC": "ARABIC",
	"_xlfn.AVERAGEIF": "AVERAGEIF",
	"_xlfn.AVERAGEIFS": "AVERAGEIFS",
	"_xlfn.BASE": "BASE",
	"_xlfn.BETA.DIST": "BETA.DIST",
	"_xlfn.BETA.INV": "BETA.INV",
	"_xlfn.BINOM.DIST": "BINOM.DIST",
	"_xlfn.BINOM.DIST.RANGE": "BINOM.DIST.RANGE",
	"_xlfn.BINOM.INV": "BINOM.INV",
	"_xlfn.BITAND": "BITAND",
	"_xlfn.BITLSHIFT": "BITLSHIFT",
	"_xlfn.BITOR": "BITOR",
	"_xlfn.BITRSHIFT": "BITRSHIFT",
	"_xlfn.BITXOR": "BITXOR",
	"_xlfn.CEILING.MATH": "CEILING.MATH",
	"_xlfn.CEILING.PRECISE": "CEILING.PRECISE",
	"_xlfn.CHISQ.DIST": "CHISQ.DIST",
	"_xlfn.CHISQ.DIST.RT": "CHISQ.DIST.RT",
	"_xlfn.CHISQ.INV": "CHISQ.INV",
	"_xlfn.CHISQ.INV.RT": "CHISQ.INV.RT",
	"_xlfn.CHISQ.TEST": "CHISQ.TEST",
	"_xlfn.COMBINA": "COMBINA",
	"_xlfn.CONFIDENCE.NORM": "CONFIDENCE.NORM",
	"_xlfn.CONFIDENCE.T": "CONFIDENCE.T",
	"_xlfn.COT": "COT",
	"_xlfn.COTH": "COTH",
	"_xlfn.COUNTIFS": "COUNTIFS",
	"_xlfn.COVARIANCE.P": "COVARIANCE.P",
	"_xlfn.COVARIANCE.S": "COVARIANCE.S",
	"_xlfn.CSC": "CSC",
	"_xlfn.CSCH": "CSCH",
	"_xlfn.DAYS": "DAYS",
	"_xlfn.DECIMAL": "DECIMAL",
	"_xlfn.ECMA.CEILING": "ECMA.CEILING",
	"_xlfn.ERF.PRECISE": "ERF.PRECISE",
	"_xlfn.ERFC.PRECISE": "ERFC.PRECISE",
	"_xlfn.EXPON.DIST": "EXPON.DIST",
	"_xlfn.F.DIST": "F.DIST",
	"_xlfn.F.DIST.RT": "F.DIST.RT",
	"_xlfn.F.INV": "F.INV",
	"_xlfn.F.INV.RT": "F.INV.RT",
	"_xlfn.F.TEST": "F.TEST",
	"_xlfn.FILTERXML": "FILTERXML",
	"_xlfn.FLOOR.MATH": "FLOOR.MATH",
	"_xlfn.FLOOR.PRECISE": "FLOOR.PRECISE",
	"_xlfn.FORMULATEXT": "FORMULATEXT",
	"_xlfn.GAMMA": "GAMMA",
	"_xlfn.GAMMA.DIST": "GAMMA.DIST",
	"_xlfn.GAMMA.INV": "GAMMA.INV",
	"_xlfn.GAMMALN.PRECISE": "GAMMALN.PRECISE",
	"_xlfn.GAUSS": "GAUSS",
	"_xlfn.HYPGEOM.DIST": "HYPGEOM.DIST",
	"_xlfn.IFNA": "IFNA",
	"_xlfn.IFERROR": "IFERROR",
	"_xlfn.IMCOSH": "IMCOSH",
	"_xlfn.IMCOT": "IMCOT",
	"_xlfn.IMCSC": "IMCSC",
	"_xlfn.IMCSCH": "IMCSCH",
	"_xlfn.IMSEC": "IMSEC",
	"_xlfn.IMSECH": "IMSECH",
	"_xlfn.IMSINH": "IMSINH",
	"_xlfn.IMTAN": "IMTAN",
	"_xlfn.ISFORMULA": "ISFORMULA",
	"_xlfn.ISO.CEILING": "ISO.CEILING",
	"_xlfn.ISOWEEKNUM": "ISOWEEKNUM",
	"_xlfn.LOGNORM.DIST": "LOGNORM.DIST",
	"_xlfn.LOGNORM.INV": "LOGNORM.INV",
	"_xlfn.MODE.MULT": "MODE.MULT",
	"_xlfn.MODE.SNGL": "MODE.SNGL",
	"_xlfn.MUNIT": "MUNIT",
	"_xlfn.NEGBINOM.DIST": "NEGBINOM.DIST",
	"_xlfn.NETWORKDAYS.INTL": "NETWORKDAYS.INTL",
	"_xlfn.NIGBINOM": "NIGBINOM",
	"_xlfn.NORM.DIST": "NORM.DIST",
	"_xlfn.NORM.INV": "NORM.INV",
	"_xlfn.NORM.S.DIST": "NORM.S.DIST",
	"_xlfn.NORM.S.INV": "NORM.S.INV",
	"_xlfn.NUMBERVALUE": "NUMBERVALUE",
	"_xlfn.PDURATION": "PDURATION",
	"_xlfn.PERCENTILE.EXC": "PERCENTILE.EXC",
	"_xlfn.PERCENTILE.INC": "PERCENTILE.INC",
	"_xlfn.PERCENTRANK.EXC": "PERCENTRANK.EXC",
	"_xlfn.PERCENTRANK.INC": "PERCENTRANK.INC",
	"_xlfn.PERMUTATIONA": "PERMUTATIONA",
	"_xlfn.PHI": "PHI",
	"_xlfn.POISSON.DIST": "POISSON.DIST",
	"_xlfn.QUARTILE.EXC": "QUARTILE.EXC",
	"_xlfn.QUARTILE.INC": "QUARTILE.INC",
	"_xlfn.QUERYSTRING": "QUERYSTRING",
	"_xlfn.RANK.AVG": "RANK.AVG",
	"_xlfn.RANK.EQ": "RANK.EQ",
	"_xlfn.RRI": "RRI",
	"_xlfn.SEC": "SEC",
	"_xlfn.SECH": "SECH",
	"_xlfn.SHEET": "SHEET",
	"_xlfn.SHEETS": "SHEETS",
	"_xlfn.SKEW.P": "SKEW.P",
	"_xlfn.STDEV.P": "STDEV.P",
	"_xlfn.STDEV.S": "STDEV.S",
	"_xlfn.SUMIFS": "SUMIFS",
	"_xlfn.T.DIST": "T.DIST",
	"_xlfn.T.DIST.2T": "T.DIST.2T",
	"_xlfn.T.DIST.RT": "T.DIST.RT",
	"_xlfn.T.INV": "T.INV",
	"_xlfn.T.INV.2T": "T.INV.2T",
	"_xlfn.T.TEST": "T.TEST",
	"_xlfn.UNICHAR": "UNICHAR",
	"_xlfn.UNICODE": "UNICODE",
	"_xlfn.VAR.P": "VAR.P",
	"_xlfn.VAR.S": "VAR.S",
	"_xlfn.WEBSERVICE": "WEBSERVICE",
	"_xlfn.WEIBULL.DIST": "WEIBULL.DIST",
	"_xlfn.WORKDAY.INTL": "WORKDAY.INTL",
	"_xlfn.XOR": "XOR",
	"_xlfn.Z.TEST": "Z.TEST"
};

/* Part 3 TODO: actually parse formulae */
function ods_to_csf_formula(f) {
	if(f.substr(0,3) == "of:") f = f.substr(3);
	/* 5.2 Basic Expressions */
	if(f.charCodeAt(0) == 61) {
		f = f.substr(1);
		if(f.charCodeAt(0) == 61) f = f.substr(1);
	}
	f = f.replace(/COM\.MICROSOFT\./g, "");
	/* Part 3 Section 5.8 References */
	f = f.replace(/\[((?:\.[A-Z]+[0-9]+)(?::\.[A-Z]+[0-9]+)?)\]/g, function($$, $1) { return $1.replace(/\./g,""); });
	/* TODO: something other than this */
	f = f.replace(/\[.(#[A-Z]*[?!])\]/g, "$1");
	return f.replace(/[;~]/g,",").replace(/\|/g,";");
}

function csf_to_ods_formula(f) {
	var o = "of:=" + f.replace(crefregex, "$1[.$2$3$4$5]").replace(/\]:\[/g,":");
	/* TODO: something other than this */
	return o.replace(/;/g, "|").replace(/,/g,";");
}

function ods_to_csf_range_3D(r) {
	var a = r.split(":");
	var s = a[0].split(".")[0];
	return [s, a[0].split(".")[1] + ":" + a[1].split(".")[1]];
}
var strs = {}; // shared strings
var _ssfopts = {}; // spreadsheet formatting options

RELS.WS = [
	"http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet",
	"http://purl.oclc.org/ooxml/officeDocument/relationships/worksheet"
];

function get_sst_id(sst, str) {
	for(var i = 0, len = sst.length; i < len; ++i) if(sst[i].t === str) { sst.Count ++; return i; }
	sst[len] = {t:str}; sst.Count ++; sst.Unique ++; return len;
}

function col_obj_w(C, col) {
	var p = ({min:C+1,max:C+1});
	/* wch (chars), wpx (pixels) */
	var wch = -1;
	if(col.MDW) MDW = col.MDW;
	if(col.width != null) p.customWidth = 1;
	else if(col.wpx != null) wch = px2char(col.wpx);
	else if(col.wch != null) wch = col.wch;
	if(wch > -1) { p.width = char2width(wch); p.customWidth = 1; }
	else if(col.width != null) p.width = col.width;
	if(col.hidden) p.hidden = true;
	return p;
}

function default_margins(margins, mode) {
	if(!margins) return;
	var defs = [0.7, 0.7, 0.75, 0.75, 0.3, 0.3];
	if(mode == 'xlml') defs = [1, 1, 1, 1, 0.5, 0.5];
	if(margins.left   == null) margins.left   = defs[0];
	if(margins.right  == null) margins.right  = defs[1];
	if(margins.top    == null) margins.top    = defs[2];
	if(margins.bottom == null) margins.bottom = defs[3];
	if(margins.header == null) margins.header = defs[4];
	if(margins.footer == null) margins.footer = defs[5];
}

function get_cell_style(styles, cell, opts) {
	var z = opts.revssf[cell.z != null ? cell.z : "General"];
	var i = 0x3c, len = styles.length;
	if(z == null && opts.ssf) {
		for(; i < 0x188; ++i) if(opts.ssf[i] == null) {
			SSF.load(cell.z, i);
			opts.ssf[i] = cell.z;
			opts.revssf[cell.z] = z = i;
			break;
		}
	}
	for(i = 0; i != len; ++i) if(styles[i].numFmtId === z) return i;
	styles[len] = {
		numFmtId:z,
		fontId:0,
		fillId:0,
		borderId:0,
		xfId:0,
		applyNumberFormat:1
	};
	return len;
}

function safe_format(p, fmtid, fillid, opts, themes, styles) {
	if(p.t === 'z') return;
	if(p.t === 'd' && typeof p.v === 'string') p.v = parseDate(p.v);
	try {
		if(opts.cellNF) p.z = SSF._table[fmtid];
	} catch(e) { if(opts.WTF) throw e; }
	if(!opts || opts.cellText !== false) try {
		if(p.t === 'e') p.w = p.w || BErr[p.v];
		else if(fmtid === 0) {
			if(p.t === 'n') {
				if((p.v|0) === p.v) p.w = SSF._general_int(p.v,_ssfopts);
				else p.w = SSF._general_num(p.v,_ssfopts);
			}
			else if(p.t === 'd') {
				var dd = datenum(p.v);
				if((dd|0) === dd) p.w = SSF._general_int(dd,_ssfopts);
				else p.w = SSF._general_num(dd,_ssfopts);
			}
			else if(p.v === undefined) return "";
			else p.w = SSF._general(p.v,_ssfopts);
		}
		else if(p.t === 'd') p.w = SSF.format(fmtid,datenum(p.v),_ssfopts);
		else p.w = SSF.format(fmtid,p.v,_ssfopts);
	} catch(e) { if(opts.WTF) throw e; }
	if(fillid) try {
		p.s = styles.Fills[fillid];
		if (p.s.fgColor && p.s.fgColor.theme && !p.s.fgColor.rgb) {
			p.s.fgColor.rgb = rgb_tint(themes.themeElements.clrScheme[p.s.fgColor.theme].rgb, p.s.fgColor.tint || 0);
			if(opts.WTF) p.s.fgColor.raw_rgb = themes.themeElements.clrScheme[p.s.fgColor.theme].rgb;
		}
		if (p.s.bgColor && p.s.bgColor.theme) {
			p.s.bgColor.rgb = rgb_tint(themes.themeElements.clrScheme[p.s.bgColor.theme].rgb, p.s.bgColor.tint || 0);
			if(opts.WTF) p.s.bgColor.raw_rgb = themes.themeElements.clrScheme[p.s.bgColor.theme].rgb;
		}
	} catch(e) { if(opts.WTF) throw e; }
}
function parse_ws_xml_dim(ws, s) {
	var d = safe_decode_range(s);
	if(d.s.r<=d.e.r && d.s.c<=d.e.c && d.s.r>=0 && d.s.c>=0) ws["!ref"] = encode_range(d);
}
var mergecregex = /<(?:\w:)?mergeCell ref="[A-Z0-9:]+"\s*[\/]?>/g;
var sheetdataregex = /<(?:\w+:)?sheetData>([^\u2603]*)<\/(?:\w+:)?sheetData>/;
var hlinkregex = /<(?:\w:)?hyperlink [^>]*>/mg;
var dimregex = /"(\w*:\w*)"/;
var colregex = /<(?:\w:)?col[^>]*[\/]?>/g;
var afregex = /<(?:\w:)?autoFilter[^>]*([\/]|>([^\u2603]*)<\/(?:\w:)?autoFilter)>/g;
var marginregex= /<(?:\w:)?pageMargins[^>]*\/>/g;
/* 18.3 Worksheets */
function parse_ws_xml(data, opts, rels, wb, themes, styles) {
	if(!data) return data;
	if(DENSE != null && opts.dense == null) opts.dense = DENSE;

	/* 18.3.1.99 worksheet CT_Worksheet */
	var s = opts.dense ? ([]) : ({});
	var refguess = ({s: {r:2000000, c:2000000}, e: {r:0, c:0} });

	var data1 = "", data2 = "";
	var mtch =data.match(sheetdataregex);
	if(mtch) {
		data1 = data.substr(0, mtch.index);
		data2 = data.substr(mtch.index + mtch[0].length);
	} else data1 = data2 = data;

	/* 18.3.1.35 dimension CT_SheetDimension ? */
	// $FlowIgnore
	var ridx = (data1.match(/<(?:\w*:)?dimension/)||{index:-1}).index;
	if(ridx > 0) {
		var ref = data1.substr(ridx,50).match(dimregex);
		if(ref) parse_ws_xml_dim(s, ref[1]);
	}

	/* 18.3.1.17 cols CT_Cols */
	var columns = [];
	if(opts.cellStyles) {
		/* 18.3.1.13 col CT_Col */
		var cols = data1.match(colregex);
		if(cols) parse_ws_xml_cols(columns, cols);
	}

	/* 18.3.1.80 sheetData CT_SheetData ? */
	if(mtch) parse_ws_xml_data(mtch[1], s, opts, refguess, themes, styles);

	/* 18.3.1.2  autoFilter CT_AutoFilter */
	var afilter = data2.match(afregex);
	if(afilter) s['!autofilter'] = parse_ws_xml_autofilter(afilter[0]);

	/* 18.3.1.55 mergeCells CT_MergeCells */
	var mergecells = [];
	var merges = data2.match(mergecregex);
	if(merges) for(ridx = 0; ridx != merges.length; ++ridx)
		mergecells[ridx] = safe_decode_range(merges[ridx].substr(merges[ridx].indexOf("\"")+1));

	/* 18.3.1.48 hyperlinks CT_Hyperlinks */
	var hlink = data2.match(hlinkregex);
	if(hlink) parse_ws_xml_hlinks(s, hlink, rels);

	/* 18.3.1.62 pageMargins CT_PageMargins */
	var margins = data2.match(marginregex);
	if(margins) s['!margins'] = parse_ws_xml_margins(parsexmltag(margins[0]));

	if(!s["!ref"] && refguess.e.c >= refguess.s.c && refguess.e.r >= refguess.s.r) s["!ref"] = encode_range(refguess);
	if(opts.sheetRows > 0 && s["!ref"]) {
		var tmpref = safe_decode_range(s["!ref"]);
		if(opts.sheetRows < +tmpref.e.r) {
			tmpref.e.r = opts.sheetRows - 1;
			if(tmpref.e.r > refguess.e.r) tmpref.e.r = refguess.e.r;
			if(tmpref.e.r < tmpref.s.r) tmpref.s.r = tmpref.e.r;
			if(tmpref.e.c > refguess.e.c) tmpref.e.c = refguess.e.c;
			if(tmpref.e.c < tmpref.s.c) tmpref.s.c = tmpref.e.c;
			s["!fullref"] = s["!ref"];
			s["!ref"] = encode_range(tmpref);
		}
	}
	if(mergecells.length > 0) s["!merges"] = mergecells;
	if(columns.length > 0) s["!cols"] = columns;
	return s;
}

function write_ws_xml_merges(merges) {
	if(merges.length == 0) return "";
	var o = '<mergeCells count="' + merges.length + '">';
	for(var i = 0; i != merges.length; ++i) o += '<mergeCell ref="' + encode_range(merges[i]) + '"/>';
	return o + '</mergeCells>';
}

/* 18.3.1.85 sheetPr CT_SheetProtection */
function write_ws_xml_protection(sp) {
	// algorithmName, hashValue, saltValue, spinCountpassword
	var o = ({sheet:1});
	var deffalse = ["objects", "scenarios", "selectLockedCells", "selectUnlockedCells"];
	var deftrue = [
		"formatColumns", "formatRows", "formatCells",
		"insertColumns", "insertRows", "insertHyperlinks",
		"deleteColumns", "deleteRows",
		"sort", "autoFilter", "pivotTables"
	];
	deffalse.forEach(function(n) { if(sp[n] != null && sp[n]) o[n] = "1"; });
	deftrue.forEach(function(n) { if(sp[n] != null && !sp[n]) o[n] = "0"; });
	/* TODO: algorithm */
	if(sp.password) o.password = crypto_CreatePasswordVerifier_Method1(sp.password).toString(16).toUpperCase();
	return writextag('sheetProtection', null, o);
}

function parse_ws_xml_hlinks(s, data, rels) {
	var dense = Array.isArray(s);
	for(var i = 0; i != data.length; ++i) {
		var val = parsexmltag(data[i], true);
		if(!val.ref) return;
		var rel = rels ? rels['!id'][val.id] : null;
		if(rel) {
			val.Target = rel.Target;
			if(val.location) val.Target += "#"+val.location;
			val.Rel = rel;
		} else {
			val.Target = val.location;
			rel = {Target: val.location, TargetMode: 'Internal'};
			val.Rel = rel;
		}
		if(val.tooltip) { val.Tooltip = val.tooltip; delete val.tooltip; }
		var rng = safe_decode_range(val.ref);
		for(var R=rng.s.r;R<=rng.e.r;++R) for(var C=rng.s.c;C<=rng.e.c;++C) {
			var addr = encode_cell({c:C,r:R});
			if(dense) {
				if(!s[R]) s[R] = [];
				if(!s[R][C]) s[R][C] = {t:"z",v:undefined};
				s[R][C].l = val;
			} else {
				if(!s[addr]) s[addr] = {t:"z",v:undefined};
				s[addr].l = val;
			}
		}
	}
}

function parse_ws_xml_margins(margin) {
	var o = {};
	["left", "right", "top", "bottom", "header", "footer"].forEach(function(k) {
		if(margin[k]) o[k] = parseFloat(margin[k]);
	});
	return o;
}
function write_ws_xml_margins(margin) {
	default_margins(margin);
	return writextag('pageMargins', null, margin);
}

function parse_ws_xml_cols(columns, cols) {
	var seencol = false;
	for(var coli = 0; coli != cols.length; ++coli) {
		var coll = parsexmltag(cols[coli], true);
		if(coll.hidden) coll.hidden = parsexmlbool(coll.hidden);
		var colm=parseInt(coll.min, 10)-1, colM=parseInt(coll.max,10)-1;
		delete coll.min; delete coll.max; coll.width = +coll.width;
		if(!seencol && coll.width) { seencol = true; find_mdw_colw(coll.width); }
		process_col(coll);
		while(colm <= colM) columns[colm++] = dup(coll);
	}
}

function write_ws_xml_cols(ws, cols) {
	var o = ["<cols>"], col, width;
	for(var i = 0; i != cols.length; ++i) {
		if(!(col = cols[i])) continue;
		o[o.length] = (writextag('col', null, col_obj_w(i, col)));
	}
	o[o.length] = "</cols>";
	return o.join("");
}

function parse_ws_xml_autofilter(data) {
	var o = { ref: (data.match(/ref="([^"]*)"/)||[])[1]};
	return o;
}
function write_ws_xml_autofilter(data) {
	return writextag("autoFilter", null, {ref:data.ref});
}

/* 18.3.1.88 sheetViews CT_SheetViews */
/* 18.3.1.87 sheetView CT_SheetView */
function write_ws_xml_sheetviews(ws, opts, idx, wb) {
	return writextag("sheetViews", writextag("sheetView", null, {workbookViewId:"0"}), {});
}

function write_ws_xml_cell(cell, ref, ws, opts, idx, wb) {
	if(cell.v === undefined && cell.f === undefined || cell.t === 'z') return "";
	var vv = "";
	var oldt = cell.t, oldv = cell.v;
	switch(cell.t) {
		case 'b': vv = cell.v ? "1" : "0"; break;
		case 'n': vv = ''+cell.v; break;
		case 'e': vv = BErr[cell.v]; break;
		case 'd':
			if(opts.cellDates) vv = parseDate(cell.v).toISOString();
			else {
				cell.t = 'n';
				vv = ''+(cell.v = datenum(parseDate(cell.v)));
			}
			if(typeof cell.z === 'undefined') cell.z = SSF._table[14];
			break;
		default: vv = cell.v; break;
	}
	var v = writetag('v', escapexml(vv)), o = ({r:ref});
	/* TODO: cell style */
	var os = get_cell_style(opts.cellXfs, cell, opts);
	if(os !== 0) o.s = os;
	switch(cell.t) {
		case 'n': break;
		case 'd': o.t = "d"; break;
		case 'b': o.t = "b"; break;
		case 'e': o.t = "e"; break;
		default: if(cell.v == null) { delete cell.t; break; }
			if(opts.bookSST) {
				v = writetag('v', ''+get_sst_id(opts.Strings, cell.v));
				o.t = "s"; break;
			}
			o.t = "str"; break;
	}
	if(cell.t != oldt) { cell.t = oldt; cell.v = oldv; }
	if(cell.f) {
		var ff = cell.F && cell.F.substr(0, ref.length) == ref ? {t:"array", ref:cell.F} : null;
		v = writextag('f', escapexml(cell.f), ff) + (cell.v != null ? v : "");
	}
	if(cell.l) ws['!links'].push([ref, cell.l]);
	if(cell.c) ws['!comments'].push([ref, cell.c]);
	return writextag('c', v, o);
}

var parse_ws_xml_data = (function parse_ws_xml_data_factory() {
	var cellregex = /<(?:\w+:)?c[ >]/, rowregex = /<\/(?:\w+:)?row>/;
	var rregex = /r=["']([^"']*)["']/, isregex = /<(?:\w+:)?is>([\S\s]*?)<\/(?:\w+:)?is>/;
	var refregex = /ref=["']([^"']*)["']/;
	var match_v = matchtag("v"), match_f = matchtag("f");

return function parse_ws_xml_data(sdata, s, opts, guess, themes, styles) {
	var ri = 0, x = "", cells = [], cref = [], idx=0, i=0, cc=0, d="", p;
	var tag, tagr = 0, tagc = 0;
	var sstr, ftag;
	var fmtid = 0, fillid = 0, do_format = Array.isArray(styles.CellXf), cf;
	var arrayf = [];
	var sharedf = [];
	var dense = Array.isArray(s);
	var rows = [], rowobj = {}, rowrite = false;
	for(var marr = sdata.split(rowregex), mt = 0, marrlen = marr.length; mt != marrlen; ++mt) {
		x = marr[mt].trim();
		var xlen = x.length;
		if(xlen === 0) continue;

		/* 18.3.1.73 row CT_Row */
		for(ri = 0; ri < xlen; ++ri) if(x.charCodeAt(ri) === 62) break; ++ri;
		tag = parsexmltag(x.substr(0,ri), true);
		tagr = tag.r != null ? parseInt(tag.r, 10) : tagr+1; tagc = -1;
		if(opts.sheetRows && opts.sheetRows < tagr) continue;
		if(guess.s.r > tagr - 1) guess.s.r = tagr - 1;
		if(guess.e.r < tagr - 1) guess.e.r = tagr - 1;

		if(opts && opts.cellStyles) {
			rowobj = {}; rowrite = false;
			if(tag.ht) { rowrite = true; rowobj.hpt = parseFloat(tag.ht); rowobj.hpx = pt2px(rowobj.hpt); }
			if(tag.hidden == "1") { rowrite = true; rowobj.hidden = true; }
			if(rowrite) rows[tagr-1] = rowobj;
		}

		/* 18.3.1.4 c CT_Cell */
		cells = x.substr(ri).split(cellregex);
		for(ri = 0; ri != cells.length; ++ri) {
			x = cells[ri].trim();
			if(x.length === 0) continue;
			cref = x.match(rregex); idx = ri; i=0; cc=0;
			x = "<c " + (x.substr(0,1)=="<"?">":"") + x;
			if(cref != null && cref.length === 2) {
				idx = 0; d=cref[1];
				for(i=0; i != d.length; ++i) {
					if((cc=d.charCodeAt(i)-64) < 1 || cc > 26) break;
					idx = 26*idx + cc;
				}
				--idx;
				tagc = idx;
			} else ++tagc;
			for(i = 0; i != x.length; ++i) if(x.charCodeAt(i) === 62) break; ++i;
			tag = parsexmltag(x.substr(0,i), true);
			if(!tag.r) tag.r = encode_cell({r:tagr-1, c:tagc});
			d = x.substr(i);
			p = ({t:""});

			if((cref=d.match(match_v))!= null && cref[1] !== '') p.v=unescapexml(cref[1]);
			if(opts.cellFormula) {
				if((cref=d.match(match_f))!= null && cref[1] !== '') {
					/* TODO: match against XLSXFutureFunctions */
					p.f=unescapexml(utf8read(cref[1])).replace(/_xlfn\./,"");
					if(cref[0].indexOf('t="array"') > -1) {
						p.F = (d.match(refregex)||[])[1];
						if(p.F.indexOf(":") > -1) arrayf.push([safe_decode_range(p.F), p.F]);
					} else if(cref[0].indexOf('t="shared"') > -1) {
						// TODO: parse formula
						ftag = parsexmltag(cref[0]);
						sharedf[parseInt(ftag.si, 10)] = [ftag, unescapexml(utf8read(cref[1]))];
					}
				} else if((cref=d.match(/<f[^>]*\/>/))) {
					ftag = parsexmltag(cref[0]);
					if(sharedf[ftag.si]) p.f = shift_formula_xlsx(sharedf[ftag.si][1], sharedf[ftag.si][0].ref, tag.r);
				}
				/* TODO: factor out contains logic */
				var _tag = decode_cell(tag.r);
				for(i = 0; i < arrayf.length; ++i)
					if(_tag.r >= arrayf[i][0].s.r && _tag.r <= arrayf[i][0].e.r)
						if(_tag.c >= arrayf[i][0].s.c && _tag.c <= arrayf[i][0].e.c)
							p.F = arrayf[i][1];
			}

			if(tag.t == null && p.v === undefined) {
				if(p.f || p.F) {
					p.v = 0; p.t = "n";
				} else if(!opts.sheetStubs) continue;
				else p.t = "z";
			}
			else p.t = tag.t || "n";
			if(guess.s.c > idx) guess.s.c = idx;
			if(guess.e.c < idx) guess.e.c = idx;
			/* 18.18.11 t ST_CellType */
			switch(p.t) {
				case 'n':
					p.v = parseFloat(p.v);
					break;
				case 's':
					sstr = strs[parseInt(p.v, 10)];
					if(typeof p.v == 'undefined') {
						if(!opts.sheetStubs) continue;
						p.t = 'z';
					}
					p.v = sstr.t;
					p.r = sstr.r;
					if(opts.cellHTML) p.h = sstr.h;
					break;
				case 'str':
					p.t = "s";
					p.v = (p.v!=null) ? utf8read(p.v) : '';
					if(opts.cellHTML) p.h = escapehtml(p.v);
					break;
				case 'inlineStr':
					cref = d.match(isregex);
					p.t = 's';
					if(cref != null && (sstr = parse_si(cref[1]))) p.v = sstr.t; else p.v = "";
					break;
				case 'b': p.v = parsexmlbool(p.v); break;
				case 'd':
					if(!opts.cellDates) { p.v = datenum(parseDate(p.v)); p.t = 'n'; }
					break;
				/* error string in .w, number in .v */
				case 'e':
					if(!opts || opts.cellText !== false) p.w = p.v;
					p.v = RBErr[p.v]; break;
			}
			/* formatting */
			fmtid = fillid = 0;
			if(do_format && tag.s !== undefined) {
				cf = styles.CellXf[tag.s];
				if(cf != null) {
					if(cf.numFmtId != null) fmtid = cf.numFmtId;
					if(opts.cellStyles && cf.fillId != null) fillid = cf.fillId;
				}
			}
			safe_format(p, fmtid, fillid, opts, themes, styles);
			if(opts.cellDates && do_format && p.t == 'n' && SSF.is_date(SSF._table[fmtid])) {
				var _d = SSF.parse_date_code(p.v); if(_d) { p.t = 'd'; p.v = new Date(Date.UTC(_d.y, _d.m-1,_d.d,_d.H,_d.M,_d.S,_d.u)); }
			}
			if(dense) {
				var _r = decode_cell(tag.r);
				if(!s[_r.r]) s[_r.r] = [];
				s[_r.r][_r.c] = p;
			} else s[tag.r] = p;
		}
	}
	if(rows.length > 0) s['!rows'] = rows;
}; })();

function write_ws_xml_data(ws, opts, idx, wb, rels) {
	var o = [], r = [], range = safe_decode_range(ws['!ref']), cell, ref, rr = "", cols = [], R=0, C=0, rows = ws['!rows'];
	var dense = Array.isArray(ws);
	for(C = range.s.c; C <= range.e.c; ++C) cols[C] = encode_col(C);
	for(R = range.s.r; R <= range.e.r; ++R) {
		r = [];
		rr = encode_row(R);
		for(C = range.s.c; C <= range.e.c; ++C) {
			ref = cols[C] + rr;
			var _cell = dense ? (ws[R]||[])[C]: ws[ref];
			if(_cell === undefined) continue;
			if((cell = write_ws_xml_cell(_cell, ref, ws, opts, idx, wb)) != null) r.push(cell);
		}
		if(r.length > 0) {
			var params = ({r:rr});
			if(rows && rows[R]) {
				var row = rows[R];
				if(row.hidden) params.hidden = 1;
				var height = -1;
				if (row.hpx) height = px2pt(row.hpx);
				else if (row.hpt) height = row.hpt;
				if (height > -1) { params.ht = height; params.customHeight = 1; }
			}
			o[o.length] = (writextag('row', r.join(""), params));
		}
	}
	return o.join("");
}

var WS_XML_ROOT = writextag('worksheet', null, {
	'xmlns': XMLNS.main[0],
	'xmlns:r': XMLNS.r
});

function write_ws_xml(idx, opts, wb, rels) {
	var o = [XML_HEADER, WS_XML_ROOT];
	var s = wb.SheetNames[idx], sidx = 0, rdata = "";
	var ws = wb.Sheets[s];
	if(ws == null) ws = {};
	var ref = ws['!ref']; if(ref == null) ref = 'A1';
	if(!rels) rels = {};
	ws['!comments'] = [];
	ws['!drawing'] = [];

	o[o.length] = (writextag('sheetPr', null, {'codeName': escapexml(wb.SheetNames[idx])}));

	o[o.length] = (writextag('dimension', null, {'ref': ref}));

	o[o.length] = write_ws_xml_sheetviews(ws, opts, idx, wb);

	/* TODO: store in WB, process styles */
	if(opts.sheetFormat) o[o.length] = (writextag('sheetFormatPr', null, {defaultRowHeight:opts.sheetFormat.defaultRowHeight||'16', baseColWidth:opts.sheetFormat.baseColWidth||'10' }));

	if(ws['!cols'] != null && ws['!cols'].length > 0) o[o.length] = (write_ws_xml_cols(ws, ws['!cols']));

	o[sidx = o.length] = '<sheetData/>';
	ws['!links'] = [];
	if(ws['!ref'] != null) {
		rdata = write_ws_xml_data(ws, opts, idx, wb, rels);
		if(rdata.length > 0) o[o.length] = (rdata);
	}
	if(o.length>sidx+1) { o[o.length] = ('</sheetData>'); o[sidx]=o[sidx].replace("/>",">"); }

	/* sheetCalcPr */

	if(ws['!protect'] != null) o[o.length] = write_ws_xml_protection(ws['!protect']);

	/* protectedRanges */
	/* scenarios */

	if(ws['!autofilter'] != null) o[o.length] = write_ws_xml_autofilter(ws['!autofilter']);

	/* sortState */
	/* dataConsolidate */
	/* customSheetViews */

	if(ws['!merges'] != null && ws['!merges'].length > 0) o[o.length] = (write_ws_xml_merges(ws['!merges']));

	/* phoneticPr */
	/* conditionalFormatting */
	/* dataValidations */

	var relc = -1, rel, rId = -1;
	if(ws['!links'].length > 0) {
		o[o.length] = "<hyperlinks>";
		ws['!links'].forEach(function(l) {
			if(!l[1].Target) return;
			rId = add_rels(rels, -1, escapexml(l[1].Target).replace(/#.*$/, ""), RELS.HLINK);
			rel = ({"ref":l[0], "r:id":"rId"+rId});
			if((relc = l[1].Target.indexOf("#")) > -1) rel.location = escapexml(l[1].Target.substr(relc+1));
			if(l[1].Tooltip) rel.tooltip = escapexml(l[1].Tooltip);
			o[o.length] = writextag("hyperlink",null,rel);
		});
		o[o.length] = "</hyperlinks>";
	}
	delete ws['!links'];

	/* printOptions */
	if (ws['!margins'] != null) o[o.length] =  write_ws_xml_margins(ws['!margins']);
	/* pageSetup */

	var hfidx = o.length;
	o[o.length] = "";

	/* rowBreaks */
	/* colBreaks */
	/* customProperties */
	/* cellWatches */
	/* ignoredErrors */
	/* smartTags */

	if(ws['!drawing'].length > 0) {
		rId = add_rels(rels, -1, "../drawings/drawing" + (idx+1) + ".xml", RELS.DRAW);
		o[o.length] = writextag("drawing", null, {"r:id":"rId" + rId});
	}
	else delete ws['!drawing'];

	if(ws['!comments'].length > 0) {
		rId = add_rels(rels, -1, "../drawings/vmlDrawing" + (idx+1) + ".vml", RELS.VML);
		o[o.length] = writextag("legacyDrawing", null, {"r:id":"rId" + rId});
		ws['!legacy'] = rId;
	}

	/* drawingHF */
	/* picture */
	/* oleObjects */
	/* controls */
	/* webPublishItems */
	/* tableParts */
	/* extList */

	if(o.length>2) { o[o.length] = ('</worksheet>'); o[1]=o[1].replace("/>",">"); }
	return o.join("");
}

/* [MS-XLSB] 2.4.718 BrtRowHdr */
function parse_BrtRowHdr(data, length) {
	var z = ({});
	var tgt = data.l + length;
	z.r = data.read_shift(4);
	data.l += 4; // TODO: ixfe
	var miyRw = data.read_shift(2);
	data.l += 1; // TODO: top/bot padding
	var flags = data.read_shift(1);
	data.l = tgt;
	if(flags & 0x10) z.hidden = true;
	if(flags & 0x20) z.hpt = miyRw / 20;
	return z;
}
function write_BrtRowHdr(R, range, ws) {
	var o = new_buf(17+8*16);
	var row = (ws['!rows']||[])[R]||{};
	o.write_shift(4, R);

	o.write_shift(4, 0); /* TODO: ixfe */

	var miyRw = 0x0140;
	if(row.hpx) miyRw = px2pt(row.hpx) * 20;
	else if(row.hpt) miyRw = row.hpt * 20;
	o.write_shift(2, miyRw);

	o.write_shift(1, 0); /* top/bot padding */

	var flags = 0x0;
	if(row.hidden) flags |= 0x10;
	if(row.hpx || row.hpt) flags |= 0x20;
	o.write_shift(1, flags);

	o.write_shift(1, 0); /* phonetic guide */

	/* [MS-XLSB] 2.5.8 BrtColSpan explains the mechanism */
	var ncolspan = 0, lcs = o.l;
	o.l += 4;

	var caddr = {r:R, c:0};
	for(var i = 0; i < 16; ++i) {
		if(range.s.c > ((i+1) << 10) || range.e.c < (i << 10)) continue;
		var first = -1, last = -1;
		for(var j = (i<<10); j < ((i+1)<<10); ++j) {
			caddr.c = j;
			var cell = Array.isArray(ws) ? (ws[caddr.r]||[])[caddr.c] : ws[encode_cell(caddr)];
			if(cell) { if(first < 0) first = j; last = j; }
		}
		if(first < 0) continue;
		++ncolspan;
		o.write_shift(4, first);
		o.write_shift(4, last);
	}

	var l = o.l;
	o.l = lcs;
	o.write_shift(4, ncolspan);
	o.l = l;

	return o.length > o.l ? o.slice(0, o.l) : o;
}
function write_row_header(ba, ws, range, R) {
	var o = write_BrtRowHdr(R, range, ws);
	if(o.length > 17) write_record(ba, 'BrtRowHdr', o);
}

/* [MS-XLSB] 2.4.812 BrtWsDim */
var parse_BrtWsDim = parse_UncheckedRfX;
var write_BrtWsDim = write_UncheckedRfX;

/* [MS-XLSB] 2.4.813 BrtWsFmtInfo */
//function write_BrtWsFmtInfo(ws, o) { }

/* [MS-XLSB] 2.4.815 BrtWsProp */
function parse_BrtWsProp(data, length) {
	var z = {};
	/* TODO: pull flags */
	data.l += 19;
	z.name = parse_XLSBCodeName(data, length - 19);
	return z;
}
function write_BrtWsProp(str, o) {
	if(o == null) o = new_buf(84+4*str.length);
	for(var i = 0; i < 3; ++i) o.write_shift(1,0);
	write_BrtColor({auto:1}, o);
	o.write_shift(-4,-1);
	o.write_shift(-4,-1);
	write_XLSBCodeName(str, o);
	return o.slice(0, o.l);
}

/* [MS-XLSB] 2.4.303 BrtCellBlank */
function parse_BrtCellBlank(data, length) {
	var cell = parse_XLSBCell(data);
	return [cell];
}
function write_BrtCellBlank(cell, ncell, o) {
	if(o == null) o = new_buf(8);
	return write_XLSBCell(ncell, o);
}


/* [MS-XLSB] 2.4.304 BrtCellBool */
function parse_BrtCellBool(data, length) {
	var cell = parse_XLSBCell(data);
	var fBool = data.read_shift(1);
	return [cell, fBool, 'b'];
}
function write_BrtCellBool(cell, ncell, o) {
	if(o == null) o = new_buf(9);
	write_XLSBCell(ncell, o);
	o.write_shift(1, cell.v ? 1 : 0);
	return o;
}

/* [MS-XLSB] 2.4.305 BrtCellError */
function parse_BrtCellError(data, length) {
	var cell = parse_XLSBCell(data);
	var bError = data.read_shift(1);
	return [cell, bError, 'e'];
}

/* [MS-XLSB] 2.4.308 BrtCellIsst */
function parse_BrtCellIsst(data, length) {
	var cell = parse_XLSBCell(data);
	var isst = data.read_shift(4);
	return [cell, isst, 's'];
}
function write_BrtCellIsst(cell, ncell, o) {
	if(o == null) o = new_buf(12);
	write_XLSBCell(ncell, o);
	o.write_shift(4, ncell.v);
	return o;
}

/* [MS-XLSB] 2.4.310 BrtCellReal */
function parse_BrtCellReal(data, length) {
	var cell = parse_XLSBCell(data);
	var value = parse_Xnum(data);
	return [cell, value, 'n'];
}
function write_BrtCellReal(cell, ncell, o) {
	if(o == null) o = new_buf(16);
	write_XLSBCell(ncell, o);
	write_Xnum(cell.v, o);
	return o;
}

/* [MS-XLSB] 2.4.311 BrtCellRk */
function parse_BrtCellRk(data, length) {
	var cell = parse_XLSBCell(data);
	var value = parse_RkNumber(data);
	return [cell, value, 'n'];
}
function write_BrtCellRk(cell, ncell, o) {
	if(o == null) o = new_buf(12);
	write_XLSBCell(ncell, o);
	write_RkNumber(cell.v, o);
	return o;
}


/* [MS-XLSB] 2.4.314 BrtCellSt */
function parse_BrtCellSt(data, length) {
	var cell = parse_XLSBCell(data);
	var value = parse_XLWideString(data);
	return [cell, value, 'str'];
}
function write_BrtCellSt(cell, ncell, o) {
	if(o == null) o = new_buf(12 + 4 * cell.v.length);
	write_XLSBCell(ncell, o);
	write_XLWideString(cell.v, o);
	return o.length > o.l ? o.slice(0, o.l) : o;
}

/* [MS-XLSB] 2.4.647 BrtFmlaBool */
function parse_BrtFmlaBool(data, length, opts) {
	var end = data.l + length;
	var cell = parse_XLSBCell(data);
	cell.r = opts['!row'];
	var value = data.read_shift(1);
	var o = [cell, value, 'b'];
	if(opts.cellFormula) {
		data.l += 2;
		var formula = parse_XLSBCellParsedFormula(data, end - data.l, opts);
		o[3] = stringify_formula(formula, null/*range*/, cell, opts.supbooks, opts);/* TODO */
	}
	else data.l = end;
	return o;
}

/* [MS-XLSB] 2.4.648 BrtFmlaError */
function parse_BrtFmlaError(data, length, opts) {
	var end = data.l + length;
	var cell = parse_XLSBCell(data);
	cell.r = opts['!row'];
	var value = data.read_shift(1);
	var o = [cell, value, 'e'];
	if(opts.cellFormula) {
		data.l += 2;
		var formula = parse_XLSBCellParsedFormula(data, end - data.l, opts);
		o[3] = stringify_formula(formula, null/*range*/, cell, opts.supbooks, opts);/* TODO */
	}
	else data.l = end;
	return o;
}

/* [MS-XLSB] 2.4.649 BrtFmlaNum */
function parse_BrtFmlaNum(data, length, opts) {
	var end = data.l + length;
	var cell = parse_XLSBCell(data);
	cell.r = opts['!row'];
	var value = parse_Xnum(data);
	var o = [cell, value, 'n'];
	if(opts.cellFormula) {
		data.l += 2;
		var formula = parse_XLSBCellParsedFormula(data, end - data.l, opts);
		o[3] = stringify_formula(formula, null/*range*/, cell, opts.supbooks, opts);/* TODO */
	}
	else data.l = end;
	return o;
}

/* [MS-XLSB] 2.4.650 BrtFmlaString */
function parse_BrtFmlaString(data, length, opts) {
	var end = data.l + length;
	var cell = parse_XLSBCell(data);
	cell.r = opts['!row'];
	var value = parse_XLWideString(data);
	var o = [cell, value, 'str'];
	if(opts.cellFormula) {
		data.l += 2;
		var formula = parse_XLSBCellParsedFormula(data, end - data.l, opts);
		o[3] = stringify_formula(formula, null/*range*/, cell, opts.supbooks, opts);/* TODO */
	}
	else data.l = end;
	return o;
}

/* [MS-XLSB] 2.4.676 BrtMergeCell */
var parse_BrtMergeCell = parse_UncheckedRfX;
var write_BrtMergeCell = write_UncheckedRfX;
/* [MS-XLSB] 2.4.108 BrtBeginMergeCells */
function write_BrtBeginMergeCells(cnt, o) {
	if(o == null) o = new_buf(4);
	o.write_shift(4, cnt);
	return o;
}

/* [MS-XLSB] 2.4.656 BrtHLink */
function parse_BrtHLink(data, length, opts) {
	var end = data.l + length;
	var rfx = parse_UncheckedRfX(data, 16);
	var relId = parse_XLNullableWideString(data);
	var loc = parse_XLWideString(data);
	var tooltip = parse_XLWideString(data);
	var display = parse_XLWideString(data);
	data.l = end;
	return {rfx:rfx, relId:relId, loc:loc, Tooltip:tooltip, display:display};
}
function write_BrtHLink(l, rId, o) {
	if(o == null) o = new_buf(50+4*l[1].Target.length);
	write_UncheckedRfX({s:decode_cell(l[0]), e:decode_cell(l[0])}, o);
	write_RelID("rId" + rId, o);
	var locidx = l[1].Target.indexOf("#");
	var loc = locidx == -1 ? "" : l[1].Target.substr(locidx+1);
	write_XLWideString(loc || "", o);
	write_XLWideString(l[1].Tooltip || "", o);
	write_XLWideString("", o);
	return o.slice(0, o.l);
}

/* [MS-XLSB] 2.4.6 BrtArrFmla */
function parse_BrtArrFmla(data, length, opts) {
	var end = data.l + length;
	var rfx = parse_RfX(data, 16);
	var fAlwaysCalc = data.read_shift(1);
	var o = [rfx]; o[2] = fAlwaysCalc;
	if(opts.cellFormula) {
		var formula = parse_XLSBArrayParsedFormula(data, end - data.l, opts);
		o[1] = formula;
	} else data.l = end;
	return o;
}

/* [MS-XLSB] 2.4.742 BrtShrFmla */
function parse_BrtShrFmla(data, length, opts) {
	var end = data.l + length;
	var rfx = parse_UncheckedRfX(data, 16);
	var o = [rfx];
	if(opts.cellFormula) {
		var formula = parse_XLSBSharedParsedFormula(data, end - data.l, opts);
		o[1] = formula;
		data.l = end;
	} else data.l = end;
	return o;
}

/* [MS-XLSB] 2.4.323 BrtColInfo */
/* TODO: once XLS ColInfo is set, combine the functions */
function write_BrtColInfo(C, col, o) {
	if(o == null) o = new_buf(18);
	var p = col_obj_w(C, col);
	o.write_shift(-4, C);
	o.write_shift(-4, C);
	o.write_shift(4, (p.width || 10) * 256);
	o.write_shift(4, 0/*ixfe*/); // style
	var flags = 0;
	if(col.hidden) flags |= 0x01;
	if(typeof p.width == 'number') flags |= 0x02;
	o.write_shift(1, flags); // bit flag
	o.write_shift(1, 0); // bit flag
	return o;
}

/* [MS-XLSB] 2.4.672 BrtMargins */
function parse_BrtMargins(data, length, opts) {
	return {
		left: parse_Xnum(data, 8),
		right: parse_Xnum(data, 8),
		top: parse_Xnum(data, 8),
		bottom: parse_Xnum(data, 8),
		header: parse_Xnum(data, 8),
		footer: parse_Xnum(data, 8)
	};
}
function write_BrtMargins(margins, o) {
	if(o == null) o = new_buf(6*8);
	default_margins(margins);
	write_Xnum(margins.left, o);
	write_Xnum(margins.right, o);
	write_Xnum(margins.top, o);
	write_Xnum(margins.bottom, o);
	write_Xnum(margins.header, o);
	write_Xnum(margins.footer, o);
	return o;
}

/* [MS-XLSB] 2.4.292 BrtBeginWsView */
function write_BrtBeginWsView(ws, o) {
	if(o == null) o = new_buf(30);
	o.write_shift(2, 924); // bit flag
	o.write_shift(4, 0);
	o.write_shift(4, 0); // view first row
	o.write_shift(4, 0); // view first col
	o.write_shift(1, 0); // gridline color ICV
	o.write_shift(1, 0);
	o.write_shift(2, 0);
	o.write_shift(2, 100); // zoom scale
	o.write_shift(2, 0);
	o.write_shift(2, 0);
	o.write_shift(2, 0);
	o.write_shift(4, 0); // workbook view id
	return o;
}

/* [MS-XLSB] 2.4.740 BrtSheetProtection */
function write_BrtSheetProtection(sp, o) {
	if(o == null) o = new_buf(16*4+2);
	o.write_shift(2, sp.password ? crypto_CreatePasswordVerifier_Method1(sp.password) : 0);
	o.write_shift(4, 1); // this record should not be written if no protection
	[
		["objects",             false], // fObjects
		["scenarios",           false], // fScenarios
		["formatCells",          true], // fFormatCells
		["formatColumns",        true], // fFormatColumns
		["formatRows",           true], // fFormatRows
		["insertColumns",        true], // fInsertColumns
		["insertRows",           true], // fInsertRows
		["insertHyperlinks",     true], // fInsertHyperlinks
		["deleteColumns",        true], // fDeleteColumns
		["deleteRows",           true], // fDeleteRows
		["selectLockedCells",   false], // fSelLockedCells
		["sort",                 true], // fSort
		["autoFilter",           true], // fAutoFilter
		["pivotTables",          true], // fPivotTables
		["selectUnlockedCells", false]  // fSelUnlockedCells
	].forEach(function(n) {
if(n[1]) o.write_shift(4, sp[n[0]] != null && !sp[n[0]] ? 1 : 0);
		else      o.write_shift(4, sp[n[0]] != null && sp[n[0]] ? 0 : 1);
	});
	return o;
}

/* [MS-XLSB] 2.1.7.61 Worksheet */
function parse_ws_bin(data, _opts, rels, wb, themes, styles) {
	if(!data) return data;
	var opts = _opts || {};
	if(!rels) rels = {'!id':{}};
	if(DENSE != null && opts.dense == null) opts.dense = DENSE;
	var s = (opts.dense ? [] : {});

	var ref;
	var refguess = {s: {r:2000000, c:2000000}, e: {r:0, c:0} };

	var pass = false, end = false;
	var row, p, cf, R, C, addr, sstr, rr, cell;
	var mergecells = [];
	opts.biff = 12;
	opts['!row'] = 0;

	var ai = 0, af = false;

	var array_formulae = [];
	var shared_formulae = {};
	var supbooks = ([[]]);
	supbooks.sharedf = shared_formulae;
	supbooks.arrayf = array_formulae;
	supbooks.SheetNames = wb.SheetNames || wb.Sheets.map(function(x) { return x.name; });
	opts.supbooks = supbooks;
	for(var i = 0; i < wb.Names.length; ++i) supbooks[0][i+1] = wb.Names[i];

	var colinfo = [], rowinfo = [];
	var defwidth = 0, defheight = 0; // twips / MDW respectively
	var seencol = false;

	recordhopper(data, function ws_parse(val, R_n, RT) {
		if(end) return;
		switch(RT) {
			case 0x0094: /* 'BrtWsDim' */
				ref = val; break;
			case 0x0000: /* 'BrtRowHdr' */
				row = val;
				if(opts.sheetRows && opts.sheetRows <= row.r) end=true;
				rr = encode_row(R = row.r);
				opts['!row'] = row.r;
				if(val.hidden || val.hpt) {
					if(val.hpt) val.hpx = pt2px(val.hpt);
					rowinfo[val.r] = val;
				}
				break;

			case 0x0002: /* 'BrtCellRk' */
			case 0x0003: /* 'BrtCellError' */
			case 0x0004: /* 'BrtCellBool' */
			case 0x0005: /* 'BrtCellReal' */
			case 0x0006: /* 'BrtCellSt' */
			case 0x0007: /* 'BrtCellIsst' */
			case 0x0008: /* 'BrtFmlaString' */
			case 0x0009: /* 'BrtFmlaNum' */
			case 0x000A: /* 'BrtFmlaBool' */
			case 0x000B: /* 'BrtFmlaError' */
				p = ({t:val[2]});
				switch(val[2]) {
					case 'n': p.v = val[1]; break;
					case 's': sstr = strs[val[1]]; p.v = sstr.t; p.r = sstr.r; break;
					case 'b': p.v = val[1] ? true : false; break;
					case 'e': p.v = val[1]; if(opts.cellText !== false) p.w = BErr[p.v]; break;
					case 'str': p.t = 's'; p.v = utf8read(val[1]); break;
				}
				if((cf = styles.CellXf[val[0].iStyleRef])) safe_format(p,cf.ifmt,null,opts, themes, styles);
				C = val[0].c;
				if(opts.dense) { if(!s[R]) s[R] = []; s[R][C] = p; }
				else s[encode_col(C) + rr] = p;
				if(opts.cellFormula) {
					af = false;
					for(ai = 0; ai < array_formulae.length; ++ai) {
						var aii = array_formulae[ai];
						if(row.r >= aii[0].s.r && row.r <= aii[0].e.r)
							if(C >= aii[0].s.c && C <= aii[0].e.c) {
								p.F = encode_range(aii[0]); af = true;
							}
					}
					if(!af && val.length > 3) p.f = val[3];
				}
				if(refguess.s.r > row.r) refguess.s.r = row.r;
				if(refguess.s.c > C) refguess.s.c = C;
				if(refguess.e.r < row.r) refguess.e.r = row.r;
				if(refguess.e.c < C) refguess.e.c = C;
				if(opts.cellDates && cf && p.t == 'n' && SSF.is_date(SSF._table[cf.ifmt])) {
					var _d = SSF.parse_date_code(p.v); if(_d) { p.t = 'd'; p.v = new Date(Date.UTC(_d.y, _d.m-1,_d.d,_d.H,_d.M,_d.S,_d.u)); }
				}
				break;

			case 0x0001: /* 'BrtCellBlank' */
				if(!opts.sheetStubs) break;
				p = ({t:'z',v:undefined});
				C = val[0].c;
				if(opts.dense) { if(!s[R]) s[R] = []; s[R][C] = p; }
				else s[encode_col(C) + rr] = p;
				if(refguess.s.r > row.r) refguess.s.r = row.r;
				if(refguess.s.c > C) refguess.s.c = C;
				if(refguess.e.r < row.r) refguess.e.r = row.r;
				if(refguess.e.c < C) refguess.e.c = C;
				break;

			case 0x00B0: /* 'BrtMergeCell' */
				mergecells.push(val); break;

			case 0x01EE: /* 'BrtHLink' */
				var rel = rels['!id'][val.relId];
				if(rel) {
					val.Target = rel.Target;
					if(val.loc) val.Target += "#"+val.loc;
					val.Rel = rel;
				}
				for(R=val.rfx.s.r;R<=val.rfx.e.r;++R) for(C=val.rfx.s.c;C<=val.rfx.e.c;++C) {
					if(opts.dense) {
						if(!s[R]) s[R] = [];
						if(!s[R][C]) s[R][C] = {t:'z',v:undefined};
						s[R][C].l = val;
					} else {
						addr = encode_cell({c:C,r:R});
						if(!s[addr]) s[addr] = {t:'z',v:undefined};
						s[addr].l = val;
					}
				}
				break;

			case 0x01AA: /* 'BrtArrFmla' */
				if(!opts.cellFormula) break;
				array_formulae.push(val);
				cell = ((opts.dense ? s[R][C] : s[encode_col(C) + rr]));
				cell.f = stringify_formula(val[1], refguess, {r:row.r, c:C}, supbooks, opts);
				cell.F = encode_range(val[0]);
				break;
			case 0x01AB: /* 'BrtShrFmla' */
				if(!opts.cellFormula) break;
				shared_formulae[encode_cell(val[0].s)] = val[1];
				cell = (opts.dense ? s[R][C] : s[encode_col(C) + rr]);
				cell.f = stringify_formula(val[1], refguess, {r:row.r, c:C}, supbooks, opts);
				break;

			/* identical to 'ColInfo' in XLS */
			case 0x003C: /* 'BrtColInfo' */
				if(!opts.cellStyles) break;
				while(val.e >= val.s) {
					colinfo[val.e--] = { width: val.w/256, hidden: !!(val.flags & 0x01) };
					if(!seencol) { seencol = true; find_mdw_colw(val.w/256); }
					process_col(colinfo[val.e+1]);
				}
				break;

			case 0x00A1: /* 'BrtBeginAFilter' */
				s['!autofilter'] = { ref:encode_range(val) };
				break;

			case 0x01DC: /* 'BrtMargins' */
				s['!margins'] = val;
				break;

			/* case 'BrtUid' */
			case 0x00AF: /* 'BrtAFilterDateGroupItem' */
			case 0x0284: /* 'BrtActiveX' */
			case 0x0271: /* 'BrtBigName' */
			case 0x0232: /* 'BrtBkHim' */
			case 0x018C: /* 'BrtBrk' */
			case 0x0458: /* 'BrtCFIcon' */
			case 0x047A: /* 'BrtCFRuleExt' */
			case 0x01D7: /* 'BrtCFVO' */
			case 0x041A: /* 'BrtCFVO14' */
			case 0x0289: /* 'BrtCellIgnoreEC' */
			case 0x0451: /* 'BrtCellIgnoreEC14' */
			case 0x0031: /* 'BrtCellMeta' */
			case 0x024D: /* 'BrtCellSmartTagProperty' */
			case 0x025F: /* 'BrtCellWatch' */
			case 0x0234: /* 'BrtColor' */
			case 0x041F: /* 'BrtColor14' */
			case 0x00A8: /* 'BrtColorFilter' */
			case 0x00AE: /* 'BrtCustomFilter' */
			case 0x049C: /* 'BrtCustomFilter14' */
			case 0x01F3: /* 'BrtDRef' */
			case 0x0040: /* 'BrtDVal' */
			case 0x041D: /* 'BrtDVal14' */
			case 0x0226: /* 'BrtDrawing' */
			case 0x00AB: /* 'BrtDynamicFilter' */
			case 0x00A7: /* 'BrtFilter' */
			case 0x0499: /* 'BrtFilter14' */
			case 0x00A9: /* 'BrtIconFilter' */
			case 0x049D: /* 'BrtIconFilter14' */
			case 0x0227: /* 'BrtLegacyDrawing' */
			case 0x0228: /* 'BrtLegacyDrawingHF' */
			case 0x0295: /* 'BrtListPart' */
			case 0x027F: /* 'BrtOleObject' */
			case 0x01DE: /* 'BrtPageSetup' */
			case 0x0097: /* 'BrtPane' */
			case 0x0219: /* 'BrtPhoneticInfo' */
			case 0x01DD: /* 'BrtPrintOptions' */
			case 0x0218: /* 'BrtRangeProtection' */
			case 0x044F: /* 'BrtRangeProtection14' */
			case 0x02A8: /* 'BrtRangeProtectionIso' */
			case 0x0450: /* 'BrtRangeProtectionIso14' */
			case 0x0400: /* 'BrtRwDescent' */
			case 0x0098: /* 'BrtSel' */
			case 0x0297: /* 'BrtSheetCalcProp' */
			case 0x0217: /* 'BrtSheetProtection' */
			case 0x02A6: /* 'BrtSheetProtectionIso' */
			case 0x01F8: /* 'BrtSlc' */
			case 0x0413: /* 'BrtSparkline' */
			case 0x01AC: /* 'BrtTable' */
			case 0x00AA: /* 'BrtTop10Filter' */
			case 0x0032: /* 'BrtValueMeta' */
			case 0x0816: /* 'BrtWebExtension' */
			case 0x01E5: /* 'BrtWsFmtInfo' */
			case 0x0415: /* 'BrtWsFmtInfoEx14' */
			case 0x0093: /* 'BrtWsProp' */
				break;

			case 0x0023: /* 'BrtFRTBegin' */
				pass = true; break;
			case 0x0024: /* 'BrtFRTEnd' */
				pass = false; break;
			case 0x0025: /* 'BrtACBegin' */ break;
			case 0x0026: /* 'BrtACEnd' */ break;

			default:
				if((R_n||"").indexOf("Begin") > 0){/* empty */}
				else if((R_n||"").indexOf("End") > 0){/* empty */}
				else if(!pass || opts.WTF) throw new Error("Unexpected record " + RT + " " + R_n);
		}
	}, opts);

	delete opts.supbooks;
	delete opts['!row'];

	if(!s["!ref"] && (refguess.s.r < 2000000 || ref && (ref.e.r > 0 || ref.e.c > 0 || ref.s.r > 0 || ref.s.c > 0))) s["!ref"] = encode_range(ref || refguess);
	if(opts.sheetRows && s["!ref"]) {
		var tmpref = safe_decode_range(s["!ref"]);
		if(opts.sheetRows < +tmpref.e.r) {
			tmpref.e.r = opts.sheetRows - 1;
			if(tmpref.e.r > refguess.e.r) tmpref.e.r = refguess.e.r;
			if(tmpref.e.r < tmpref.s.r) tmpref.s.r = tmpref.e.r;
			if(tmpref.e.c > refguess.e.c) tmpref.e.c = refguess.e.c;
			if(tmpref.e.c < tmpref.s.c) tmpref.s.c = tmpref.e.c;
			s["!fullref"] = s["!ref"];
			s["!ref"] = encode_range(tmpref);
		}
	}
	if(mergecells.length > 0) s["!merges"] = mergecells;
	if(colinfo.length > 0) s["!cols"] = colinfo;
	if(rowinfo.length > 0) s["!rows"] = rowinfo;
	return s;
}

/* TODO: something useful -- this is a stub */
function write_ws_bin_cell(ba, cell, R, C, opts, ws) {
	if(cell.v === undefined) return "";
	var vv = ""; var olddate = null;
	switch(cell.t) {
		case 'b': vv = cell.v ? "1" : "0"; break;
		case 'd': // no BrtCellDate :(
			cell.z = cell.z || SSF._table[14];
			olddate = cell.v;
			cell.v = datenum((cell.v)); cell.t = 'n';
			break;
		/* falls through */
		case 'n': case 'e': vv = ''+cell.v; break;
		default: vv = cell.v; break;
	}
	var o = ({r:R, c:C});
	/* TODO: cell style */
	o.s = get_cell_style(opts.cellXfs, cell, opts);
	if(cell.l) ws['!links'].push([encode_cell(o), cell.l]);
	if(cell.c) ws['!comments'].push([encode_cell(o), cell.c]);
	switch(cell.t) {
		case 's': case 'str':
			if(opts.bookSST) {
				vv = get_sst_id(opts.Strings, (cell.v));
				o.t = "s"; o.v = vv;
				write_record(ba, "BrtCellIsst", write_BrtCellIsst(cell, o));
			} else {
				o.t = "str";
				write_record(ba, "BrtCellSt", write_BrtCellSt(cell, o));
			}
			return;
		case 'n':
			/* TODO: determine threshold for Real vs RK */
			if(cell.v == (cell.v | 0) && cell.v > -1000 && cell.v < 1000) write_record(ba, "BrtCellRk", write_BrtCellRk(cell, o));
			else write_record(ba, "BrtCellReal", write_BrtCellReal(cell, o));
			if(olddate) { cell.t = 'd'; cell.v = olddate; }
			return;
		case 'b':
			o.t = "b";
			write_record(ba, "BrtCellBool", write_BrtCellBool(cell, o));
			return;
		case 'e': /* TODO: error */ o.t = "e"; break;
	}
	write_record(ba, "BrtCellBlank", write_BrtCellBlank(cell, o));
}

function write_CELLTABLE(ba, ws, idx, opts, wb) {
	var range = safe_decode_range(ws['!ref'] || "A1"), ref, rr = "", cols = [];
	write_record(ba, 'BrtBeginSheetData');
	var dense = Array.isArray(ws);
	for(var R = range.s.r; R <= range.e.r; ++R) {
		rr = encode_row(R);
		/* [ACCELLTABLE] */
		/* BrtRowHdr */
		write_row_header(ba, ws, range, R);
		for(var C = range.s.c; C <= range.e.c; ++C) {
			/* *16384CELL */
			if(R === range.s.r) cols[C] = encode_col(C);
			ref = cols[C] + rr;
			var cell = dense ? (ws[R]||[])[C] : ws[ref];
			if(!cell) continue;
			/* write cell */
			write_ws_bin_cell(ba, cell, R, C, opts, ws);
		}
	}
	write_record(ba, 'BrtEndSheetData');
}

function write_MERGECELLS(ba, ws) {
	if(!ws || !ws['!merges']) return;
	write_record(ba, 'BrtBeginMergeCells', write_BrtBeginMergeCells(ws['!merges'].length));
	ws['!merges'].forEach(function(m) { write_record(ba, 'BrtMergeCell', write_BrtMergeCell(m)); });
	write_record(ba, 'BrtEndMergeCells');
}

function write_COLINFOS(ba, ws, idx, opts, wb) {
	if(!ws || !ws['!cols']) return;
	write_record(ba, 'BrtBeginColInfos');
	ws['!cols'].forEach(function(m, i) { if(m) write_record(ba, 'BrtColInfo', write_BrtColInfo(i, m)); });
	write_record(ba, 'BrtEndColInfos');
}

function write_HLINKS(ba, ws, rels) {
	/* *BrtHLink */
	ws['!links'].forEach(function(l) {
		if(!l[1].Target) return;
		var rId = add_rels(rels, -1, l[1].Target.replace(/#.*$/, ""), RELS.HLINK);
		write_record(ba, "BrtHLink", write_BrtHLink(l, rId));
	});
	delete ws['!links'];
}
function write_LEGACYDRAWING(ba, ws, idx, rels) {
	/* [BrtLegacyDrawing] */
	if(ws['!comments'].length > 0) {
		var rId = add_rels(rels, -1, "../drawings/vmlDrawing" + (idx+1) + ".vml", RELS.VML);
		write_record(ba, "BrtLegacyDrawing", write_RelID("rId" + rId));
		ws['!legacy'] = rId;
	}
}

function write_AUTOFILTER(ba, ws) {
	if(!ws['!autofilter']) return;
	write_record(ba, "BrtBeginAFilter", write_UncheckedRfX(decode_range(ws['!autofilter'].ref)));
	/* *FILTERCOLUMN */
	/* [SORTSTATE] */
	/* BrtEndAFilter */
	write_record(ba, "BrtEndAFilter");
}

function write_WSVIEWS2(ba, ws) {
	write_record(ba, "BrtBeginWsViews");
	{ /* 1*WSVIEW2 */
		/* [ACUID] */
		write_record(ba, "BrtBeginWsView", write_BrtBeginWsView(ws));
		/* [BrtPane] */
		/* *4BrtSel */
		/* *4SXSELECT */
		/* *FRT */
		write_record(ba, "BrtEndWsView");
	}
	/* *FRT */
	write_record(ba, "BrtEndWsViews");
}

function write_WSFMTINFO(ba, ws) {
	/* [ACWSFMTINFO] */
	//write_record(ba, "BrtWsFmtInfo", write_BrtWsFmtInfo(ws));
}

function write_SHEETPROTECT(ba, ws) {
	if(!ws['!protect']) return;
	/* [BrtSheetProtectionIso] */
	write_record(ba, "BrtSheetProtection", write_BrtSheetProtection(ws['!protect']));
}

function write_ws_bin(idx, opts, wb, rels) {
	var ba = buf_array();
	var s = wb.SheetNames[idx], ws = wb.Sheets[s] || {};
	var r = safe_decode_range(ws['!ref'] || "A1");
	ws['!links'] = [];
	/* passed back to write_zip and removed there */
	ws['!comments'] = [];
	write_record(ba, "BrtBeginSheet");
	write_record(ba, "BrtWsProp", write_BrtWsProp(s));
	write_record(ba, "BrtWsDim", write_BrtWsDim(r));
	write_WSVIEWS2(ba, ws);
	write_WSFMTINFO(ba, ws);
	write_COLINFOS(ba, ws, idx, opts, wb);
	write_CELLTABLE(ba, ws, idx, opts, wb);
	/* [BrtSheetCalcProp] */
	write_SHEETPROTECT(ba, ws);
	/* *([BrtRangeProtectionIso] BrtRangeProtection) */
	/* [SCENMAN] */
	write_AUTOFILTER(ba, ws);
	/* [SORTSTATE] */
	/* [DCON] */
	/* [USERSHVIEWS] */
	write_MERGECELLS(ba, ws);
	/* [BrtPhoneticInfo] */
	/* *CONDITIONALFORMATTING */
	/* [DVALS] */
	write_HLINKS(ba, ws, rels);
	/* [BrtPrintOptions] */
	if(ws['!margins']) write_record(ba, "BrtMargins", write_BrtMargins(ws['!margins']));
	/* [BrtPageSetup] */
	/* [HEADERFOOTER] */
	/* [RWBRK] */
	/* [COLBRK] */
	/* *BrtBigName */
	/* [CELLWATCHES] */
	/* [IGNOREECS] */
	/* [SMARTTAGS] */
	/* [BrtDrawing] */
	write_LEGACYDRAWING(ba, ws, idx, rels);
	/* [BrtLegacyDrawingHF] */
	/* [BrtBkHim] */
	/* [OLEOBJECTS] */
	/* [ACTIVEXCONTROLS] */
	/* [WEBPUBITEMS] */
	/* [LISTPARTS] */
	/* FRTWORKSHEET */
	write_record(ba, "BrtEndSheet");
	return ba.end();
}
function parse_numCache(data) {
	var col = [];

	/* 21.2.2.150 pt CT_NumVal */
	(data.match(/<c:pt idx="(\d*)">(.*?)<\/c:pt>/mg)||[]).forEach(function(pt) {
		var q = pt.match(/<c:pt idx="(.*?)"><c:v>(.*)<\/c:v><\/c:pt>/);
		if(!q) return;
		col[+q[1]] = +q[2];
	});

	/* 21.2.2.71 formatCode CT_Xstring */
	var nf = unescapexml((data.match(/<c:formatCode>(.*?)<\/c:formatCode>/) || ["","General"])[1]);

	return [col, nf];
}

/* 21.2 DrawingML - Charts */
function parse_chart(data, name, opts, rels, wb, csheet) {
	var cs = ((csheet || {"!type":"chart"}));
	if(!data) return csheet;
	/* 21.2.2.27 chart CT_Chart */

	var C = 0, R = 0, col = "A";
	var refguess = {s: {r:2000000, c:2000000}, e: {r:0, c:0} };

	/* 21.2.2.120 numCache CT_NumData */
	(data.match(/<c:numCache>.*?<\/c:numCache>/gm)||[]).forEach(function(nc) {
		var cache = parse_numCache(nc);
		refguess.s.r = refguess.s.c = 0;
		refguess.e.c = C;
		col = encode_col(C);
		cache[0].forEach(function(n,i) {
			cs[col + encode_row(i)] = {t:'n', v:n, z:cache[1] };
			R = i;
		});
		if(refguess.e.r < R) refguess.e.r = R;
		++C;
	});
	if(C > 0) cs["!ref"] = encode_range(refguess);
	return cs;
}
RELS.CS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/chartsheet";

var CS_XML_ROOT = writextag('chartsheet', null, {
	'xmlns': XMLNS.main[0],
	'xmlns:r': XMLNS.r
});

/* 18.3 Worksheets also covers Chartsheets */
function parse_cs_xml(data, opts, rels, wb, themes, styles) {
	if(!data) return data;
	/* 18.3.1.12 chartsheet CT_ChartSheet */
	if(!rels) rels = {'!id':{}};
	var s = {'!type':"chart", '!chart':null, '!rel':""};
	var m;

	/* 18.3.1.36 drawing CT_Drawing */
	if((m = data.match(/drawing r:id="(.*?)"/))) s['!rel'] = m[1];

	if(rels['!id'][s['!rel']]) s['!chart'] = rels['!id'][s['!rel']];
	return s;
}
function write_cs_xml(idx, opts, wb, rels) {
	var o = [XML_HEADER, CS_XML_ROOT];
	o[o.length] = writextag("drawing", null, {"r:id": "rId1"});
	add_rels(rels, -1, "../drawings/drawing" + (idx+1) + ".xml", RELS.DRAW);
	if(o.length>2) { o[o.length] = ('</chartsheet>'); o[1]=o[1].replace("/>",">"); }
	return o.join("");
}

/* [MS-XLSB] 2.1.7.7 Chart Sheet */
function parse_cs_bin(data, opts, rels, wb, themes, styles) {
	if(!data) return data;
	if(!rels) rels = {'!id':{}};
	var s = {'!type':"chart", '!chart':null, '!rel':""};
	var state = [];
	var pass = false;
	recordhopper(data, function cs_parse(val, R_n, RT) {
		switch(RT) {

			case 0x0226: /* 'BrtDrawing' */
				s['!rel'] = val; break;

			/* case 'BrtUid': */
			case 0x0232: /* 'BrtBkHim' */
			case 0x028C: /* 'BrtCsPageSetup' */
			case 0x028B: /* 'BrtCsProp' */
			case 0x029D: /* 'BrtCsProtection' */
			case 0x02A7: /* 'BrtCsProtectionIso' */
			case 0x0227: /* 'BrtLegacyDrawing' */
			case 0x0228: /* 'BrtLegacyDrawingHF' */
			case 0x01DC: /* 'BrtMargins' */
				break;

			case 0x0023: /* 'BrtFRTBegin' */
				pass = true; break;
			case 0x0024: /* 'BrtFRTEnd' */
				pass = false; break;
			case 0x0025: /* 'BrtACBegin' */
				state.push(R_n); break;
			case 0x0026: /* 'BrtACEnd' */
				state.pop(); break;

			default:
				if((R_n||"").indexOf("Begin") > 0) state.push(R_n);
				else if((R_n||"").indexOf("End") > 0) state.pop();
				else if(!pass || opts.WTF) throw new Error("Unexpected record " + RT + " " + R_n);
		}
	}, opts);

	if(rels['!id'][s['!rel']]) s['!chart'] = rels['!id'][s['!rel']];
	return s;
}
function write_cs_bin(idx, opts, wb, rels) {
	var ba = buf_array();
	write_record(ba, "BrtBeginSheet");
	/* [BrtCsProp] */
	/* CSVIEWS */
	/* [[BrtCsProtectionIso] BrtCsProtection] */
	/* [USERCSVIEWS] */
	/* [BrtMargins] */
	/* [BrtCsPageSetup] */
	/* [HEADERFOOTER] */
	/* BrtDrawing */
	/* [BrtLegacyDrawing] */
	/* [BrtLegacyDrawingHF] */
	/* [BrtBkHim] */
	/* [WEBPUBITEMS] */
	/* FRTCHARTSHEET */
	write_record(ba, "BrtEndSheet");
	return ba.end();
}
/* 18.2.28 (CT_WorkbookProtection) Defaults */
var WBPropsDef = [
	['allowRefreshQuery', '0'],
	['autoCompressPictures', '1'],
	['backupFile', '0'],
	['checkCompatibility', '0'],
	['codeName', ''],
	['date1904', '0'],
	['dateCompatibility', '1'],
	//['defaultThemeVersion', '0'],
	['filterPrivacy', '0'],
	['hidePivotFieldList', '0'],
	['promptedSolutions', '0'],
	['publishItems', '0'],
	['refreshAllConnections', false],
	['saveExternalLinkValues', '1'],
	['showBorderUnselectedTables', '1'],
	['showInkAnnotation', '1'],
	['showObjects', 'all'],
	['showPivotChartFilter', '0']
	//['updateLinks', 'userSet']
];

/* 18.2.30 (CT_BookView) Defaults */
var WBViewDef = [
	['activeTab', '0'],
	['autoFilterDateGrouping', '1'],
	['firstSheet', '0'],
	['minimized', '0'],
	['showHorizontalScroll', '1'],
	['showSheetTabs', '1'],
	['showVerticalScroll', '1'],
	['tabRatio', '600'],
	['visibility', 'visible']
	//window{Height,Width}, {x,y}Window
];

/* 18.2.19 (CT_Sheet) Defaults */
var SheetDef = [
	//['state', 'visible']
];

/* 18.2.2  (CT_CalcPr) Defaults */
var CalcPrDef = [
	['calcCompleted', 'true'],
	['calcMode', 'auto'],
	['calcOnSave', 'true'],
	['concurrentCalc', 'true'],
	['fullCalcOnLoad', 'false'],
	['fullPrecision', 'true'],
	['iterate', 'false'],
	['iterateCount', '100'],
	['iterateDelta', '0.001'],
	['refMode', 'A1']
];

/* 18.2.3 (CT_CustomWorkbookView) Defaults */
var CustomWBViewDef = [
	['autoUpdate', 'false'],
	['changesSavedWin', 'false'],
	['includeHiddenRowCol', 'true'],
	['includePrintSettings', 'true'],
	['maximized', 'false'],
	['minimized', 'false'],
	['onlySync', 'false'],
	['personalView', 'false'],
	['showComments', 'commIndicator'],
	['showFormulaBar', 'true'],
	['showHorizontalScroll', 'true'],
	['showObjects', 'all'],
	['showSheetTabs', 'true'],
	['showStatusbar', 'true'],
	['showVerticalScroll', 'true'],
	['tabRatio', '600'],
	['xWindow', '0'],
	['yWindow', '0']
];

function push_defaults_array(target, defaults) {
	for(var j = 0; j != target.length; ++j) { var w = target[j];
		for(var i=0; i != defaults.length; ++i) { var z = defaults[i];
			if(w[z[0]] == null) w[z[0]] = z[1];
		}
	}
}
function push_defaults(target, defaults) {
	for(var i = 0; i != defaults.length; ++i) { var z = defaults[i];
		if(target[z[0]] == null) target[z[0]] = z[1];
	}
}

function parse_wb_defaults(wb) {
	push_defaults(wb.WBProps, WBPropsDef);
	push_defaults(wb.CalcPr, CalcPrDef);

	push_defaults_array(wb.WBView, WBViewDef);
	push_defaults_array(wb.Sheets, SheetDef);

	_ssfopts.date1904 = parsexmlbool(wb.WBProps.date1904, 'date1904');
}

var badchars = "][*?\/\\".split("");
function check_ws_name(n, safe) {
	if(n.length > 31) { if(safe) return false; throw new Error("Sheet names cannot exceed 31 chars"); }
	var _good = true;
	badchars.forEach(function(c) {
		if(n.indexOf(c) == -1) return;
		if(!safe) throw new Error("Sheet name cannot contain : \\ / ? * [ ]");
		_good = false;
	});
	return _good;
}
function check_wb_names(N) {
	N.forEach(function(n,i) {
		check_ws_name(n);
		for(var j = 0; j < i; ++j) if(n == N[j]) throw new Error("Duplicate Sheet Name: " + n);
	});
}
function check_wb(wb) {
	if(!wb || !wb.SheetNames || !wb.Sheets) throw new Error("Invalid Workbook");
	check_wb_names(wb.SheetNames);
	/* TODO: validate workbook */
}
/* 18.2 Workbook */
var wbnsregex = /<\w+:workbook/;
function parse_wb_xml(data, opts) {
	if(!data) throw new Error("Could not find file");
	var wb = { AppVersion:{}, WBProps:{}, WBView:[], Sheets:[], CalcPr:{}, Names:[], xmlns: "" };
	var pass = false, xmlns = "xmlns";
	var dname = {}, dnstart = 0;
	/*(data.match(tagregex)||[]).forEach */
	data.replace(tagregex, function xml_wb(x, idx) {
		var y = parsexmltag(x);
		switch(strip_ns(y[0])) {
			case '<?xml': break;

			/* 18.2.27 workbook CT_Workbook 1 */
			case '<workbook':
				if(x.match(wbnsregex)) xmlns = "xmlns" + x.match(/<(\w+):/)[1];
				wb.xmlns = y[xmlns];
				break;
			case '</workbook>': break;

			/* 18.2.13 fileVersion CT_FileVersion ? */
			case '<fileVersion': delete y[0]; wb.AppVersion = y; break;
			case '<fileVersion/>': case '</fileVersion>': break;

			/* 18.2.12 fileSharing CT_FileSharing ? */
			case '<fileSharing': case '<fileSharing/>': break;

			/* 18.2.28 workbookPr CT_WorkbookPr ? */
			case '<workbookPr': delete y[0]; wb.WBProps = y; break;
			case '<workbookPr/>': delete y[0]; wb.WBProps = y; break;
			case '</workbookPr>': break;

			/* 18.2.29 workbookProtection CT_WorkbookProtection ? */
			case '<workbookProtection': break;
			case '<workbookProtection/>': break;

			/* 18.2.1  bookViews CT_BookViews ? */
			case '<bookViews>': case '</bookViews>': break;
			/* 18.2.30   workbookView CT_BookView + */
			case '<workbookView': delete y[0]; wb.WBView.push(y); break;
			case '</workbookView>': break;

			/* 18.2.20 sheets CT_Sheets 1 */
			case '<sheets>': case '</sheets>': break; // aggregate sheet
			/* 18.2.19   sheet CT_Sheet + */
			case '<sheet':
				switch(y.state) {
					case "hidden": y.Hidden = 1; break;
					case "veryHidden": y.Hidden = 2; break;
					default: y.Hidden = 0;
				}
				delete y.state;
				y.name = unescapexml(utf8read(y.name));
				delete y[0]; wb.Sheets.push(y); break;
			case '</sheet>': break;

			/* 18.2.15 functionGroups CT_FunctionGroups ? */
			case '<functionGroups': case '<functionGroups/>': break;
			/* 18.2.14   functionGroup CT_FunctionGroup + */
			case '<functionGroup': break;

			/* 18.2.9  externalReferences CT_ExternalReferences ? */
			case '<externalReferences': case '</externalReferences>': case '<externalReferences>': break;
			/* 18.2.8    externalReference CT_ExternalReference + */
			case '<externalReference': break;

			/* 18.2.6  definedNames CT_DefinedNames ? */
			case '<definedNames/>': break;
			case '<definedNames>': case '<definedNames': pass=true; break;
			case '</definedNames>': pass=false; break;
			/* 18.2.5    definedName CT_DefinedName + */
			case '<definedName': {
				dname = {};
				dname.Name = y.name;
				if(y.comment) dname.Comment = y.comment;
				if(y.localSheetId) dname.Sheet = +y.localSheetId;
				dnstart = idx + x.length;
			}	break;
			case '</definedName>': {
				dname.Ref = data.slice(dnstart, idx);
				wb.Names.push(dname);
			} break;
			case '<definedName/>': break;

			/* 18.2.2  calcPr CT_CalcPr ? */
			case '<calcPr': delete y[0]; wb.CalcPr = y; break;
			case '<calcPr/>': delete y[0]; wb.CalcPr = y; break;
			case '</calcPr>': break;

			/* 18.2.16 oleSize CT_OleSize ? (ref required) */
			case '<oleSize': break;

			/* 18.2.4  customWorkbookViews CT_CustomWorkbookViews ? */
			case '<customWorkbookViews>': case '</customWorkbookViews>': case '<customWorkbookViews': break;
			/* 18.2.3    customWorkbookView CT_CustomWorkbookView + */
			case '<customWorkbookView': case '</customWorkbookView>': break;

			/* 18.2.18 pivotCaches CT_PivotCaches ? */
			case '<pivotCaches>': case '</pivotCaches>': case '<pivotCaches': break;
			/* 18.2.17 pivotCache CT_PivotCache ? */
			case '<pivotCache': break;

			/* 18.2.21 smartTagPr CT_SmartTagPr ? */
			case '<smartTagPr': case '<smartTagPr/>': break;

			/* 18.2.23 smartTagTypes CT_SmartTagTypes ? */
			case '<smartTagTypes': case '<smartTagTypes>': case '</smartTagTypes>': break;
			/* 18.2.22   smartTagType CT_SmartTagType ? */
			case '<smartTagType': break;

			/* 18.2.24 webPublishing CT_WebPublishing ? */
			case '<webPublishing': case '<webPublishing/>': break;

			/* 18.2.11 fileRecoveryPr CT_FileRecoveryPr ? */
			case '<fileRecoveryPr': case '<fileRecoveryPr/>': break;

			/* 18.2.26 webPublishObjects CT_WebPublishObjects ? */
			case '<webPublishObjects>': case '<webPublishObjects': case '</webPublishObjects>': break;
			/* 18.2.25 webPublishObject CT_WebPublishObject ? */
			case '<webPublishObject': break;

			/* 18.2.10 extLst CT_ExtensionList ? */
			case '<extLst>': case '</extLst>': case '<extLst/>': break;
			/* 18.2.7    ext CT_Extension + */
			case '<ext': pass=true; break; //TODO: check with versions of excel
			case '</ext>': pass=false; break;

			/* Others */
			case '<ArchID': break;
			case '<AlternateContent': pass=true; break;
			case '</AlternateContent>': pass=false; break;

			default: if(!pass && opts.WTF) throw new Error('unrecognized ' + y[0] + ' in workbook');
		}
		return x;
	});
	if(XMLNS.main.indexOf(wb.xmlns) === -1) throw new Error("Unknown Namespace: " + wb.xmlns);

	parse_wb_defaults(wb);

	return wb;
}

var WB_XML_ROOT = writextag('workbook', null, {
	'xmlns': XMLNS.main[0],
	//'xmlns:mx': XMLNS.mx,
	//'xmlns:s': XMLNS.main[0],
	'xmlns:r': XMLNS.r
});

function safe1904(wb) {
	/* TODO: store date1904 somewhere else */
	if(!wb.Workbook) return "false";
	if(!wb.Workbook.WBProps) return "false";
	// $FlowIgnore
	return parsexmlbool(wb.Workbook.WBProps.date1904) ? "true" : "false";
}

function write_wb_xml(wb, opts) {
	var o = [XML_HEADER];
	o[o.length] = WB_XML_ROOT;

	var write_names = (wb.Workbook && (wb.Workbook.Names||[]).length > 0);

	/* fileVersion */
	/* fileSharing */

	o[o.length] = (writextag('workbookPr', null, {date1904:safe1904(wb), codeName:"ThisWorkbook"}));

	/* workbookProtection */
	/* bookViews */

	o[o.length] = "<sheets>";
	var sheets = wb.Workbook && wb.Workbook.Sheets || [];
	for(var i = 0; i != wb.SheetNames.length; ++i) {
		var sht = ({name:escapexml(wb.SheetNames[i].substr(0,31))});
		sht.sheetId = ""+(i+1);
		sht["r:id"] = "rId"+(i+1);
		if(sheets[i]) switch(sheets[i].Hidden) {
			case 1: sht.state = "hidden"; break;
			case 2: sht.state = "veryHidden"; break;
		}
		o[o.length] = (writextag('sheet',null,sht));
	}
	o[o.length] = "</sheets>";

	/* functionGroups */
	/* externalReferences */

	if(write_names) {
		o[o.length] = "<definedNames>";
		if(wb.Workbook && wb.Workbook.Names) wb.Workbook.Names.forEach(function(n) {
			var d = {name:n.Name};
			if(n.Comment) d.comment = n.Comment;
			if(n.Sheet != null) d.localSheetId = ""+n.Sheet;
			if(!n.Ref) return;
			o[o.length] = writextag('definedName', String(n.Ref), d);
		});
		o[o.length] = "</definedNames>";
	}

	/* calcPr */
	/* oleSize */
	/* customWorkbookViews */
	/* pivotCaches */
	/* smartTagPr */
	/* smartTagTypes */
	/* webPublishing */
	/* fileRecoveryPr */
	/* webPublishObjects */
	/* extLst */

	if(o.length>2){ o[o.length] = '</workbook>'; o[1]=o[1].replace("/>",">"); }
	return o.join("");
}
/* [MS-XLSB] 2.4.301 BrtBundleSh */
function parse_BrtBundleSh(data, length) {
	var z = {};
	z.Hidden = data.read_shift(4); //hsState ST_SheetState
	z.iTabID = data.read_shift(4);
	z.strRelID = parse_RelID(data,length-8);
	z.name = parse_XLWideString(data);
	return z;
}
function write_BrtBundleSh(data, o) {
	if(!o) o = new_buf(127);
	o.write_shift(4, data.Hidden);
	o.write_shift(4, data.iTabID);
	write_RelID(data.strRelID, o);
	write_XLWideString(data.name.substr(0,31), o);
	return o.length > o.l ? o.slice(0, o.l) : o;
}

/* [MS-XLSB] 2.4.807 BrtWbProp */
function parse_BrtWbProp(data, length) {
	data.read_shift(4);
	var dwThemeVersion = data.read_shift(4);
	var strName = (length > 8) ? parse_XLWideString(data) : "";
	return [dwThemeVersion, strName];
}
function write_BrtWbProp(data, o) {
	if(!o) o = new_buf(72);
	o.write_shift(4, 0);
	o.write_shift(4, 0);
	write_XLSBCodeName("ThisWorkbook", o);
	return o.slice(0, o.l);
}

function parse_BrtFRTArchID$(data, length) {
	var o = {};
	data.read_shift(4);
	o.ArchID = data.read_shift(4);
	data.l += length - 8;
	return o;
}

/* [MS-XLSB] 2.4.680 BrtName */
function parse_BrtName(data, length, opts) {
	var end = data.l + length;
	var flags = data.read_shift(4);
	var chKey = data.read_shift(1);
	var itab = data.read_shift(4);
	var name = parse_XLNameWideString(data);
	var formula = parse_XLSBNameParsedFormula(data, 0, opts);
	var comment = parse_XLNullableWideString(data);
	//if(0 /* fProc */) {
		// unusedstring1: XLNullableWideString
		// description: XLNullableWideString
		// helpTopic: XLNullableWideString
		// unusedstring2: XLNullableWideString
	//}
	data.l = end;
	var out = ({Name:name, Ptg:formula, Comment:comment});
	if(itab < 0xFFFFFFF) out.Sheet = itab;
	return out;
}

/* [MS-XLSB] 2.1.7.60 Workbook */
function parse_wb_bin(data, opts) {
	var wb = { AppVersion:{}, WBProps:{}, WBView:[], Sheets:[], CalcPr:{}, xmlns: "" };
	var pass = false, z;

	if(!opts) opts = {};
	opts.biff = 12;

	var Names = [];
	var supbooks = ([]);
	supbooks.SheetNames = [];

	recordhopper(data, function hopper_wb(val, R_n, RT) {
		switch(RT) {
			case 0x009C: /* 'BrtBundleSh' */
				supbooks.SheetNames.push(val.name);
				wb.Sheets.push(val); break;

			case 0x0027: /* 'BrtName' */
				val.Ref = stringify_formula(val.Ptg, null, null, supbooks, opts);
				delete val.Ptg;
				Names.push(val);
				break;
			case 0x040C: /* 'BrtNameExt' */ break;

			/* case 'BrtModelTimeGroupingCalcCol' */
			/* case 'BrtRevisionPtr' */
			/* case 'BrtUid' */
			case 0x0817: /* 'BrtAbsPath15' */
			case 0x0216: /* 'BrtBookProtection' */
			case 0x02A5: /* 'BrtBookProtectionIso' */
			case 0x009E: /* 'BrtBookView' */
			case 0x009D: /* 'BrtCalcProp' */
			case 0x0262: /* 'BrtCrashRecErr' */
			case 0x0802: /* 'BrtDecoupledPivotCacheID' */
			case 0x016A: /* 'BrtExternSheet' */
			case 0x009B: /* 'BrtFileRecover' */
			case 0x0224: /* 'BrtFileSharing' */
			case 0x02A4: /* 'BrtFileSharingIso' */
			case 0x0080: /* 'BrtFileVersion' */
			case 0x0299: /* 'BrtFnGroup' */
			case 0x0850: /* 'BrtModelRelationship' */
			case 0x084D: /* 'BrtModelTable' */
			case 0x0225: /* 'BrtOleSize' */
			case 0x0805: /* 'BrtPivotTableRef' */
			case 0x0169: /* 'BrtPlaceholderName' */
			case 0x0254: /* 'BrtSmartTagType' */
			case 0x029B: /* 'BrtSupAddin' */
			case 0x0163: /* 'BrtSupBookSrc' */
			case 0x0166: /* 'BrtSupSame' */
			case 0x0165: /* 'BrtSupSelf' */
			case 0x081C: /* 'BrtTableSlicerCacheID' */
			case 0x081B: /* 'BrtTableSlicerCacheIDs' */
			case 0x0822: /* 'BrtTimelineCachePivotCacheID' */
			case 0x018D: /* 'BrtUserBookView' */
			case 0x009A: /* 'BrtWbFactoid' */
			case 0x0099: /* 'BrtWbProp' */
			case 0x045D: /* 'BrtWbProp14' */
			case 0x0229: /* 'BrtWebOpt' */
			case 0x082B: /* 'BrtWorkBookPr15' */
				break;

			case 0x0023: /* 'BrtFRTBegin' */
				pass = true; break;
			case 0x0024: /* 'BrtFRTEnd' */
				pass = false; break;
			case 0x0025: /* 'BrtACBegin' */ break;
			case 0x0026: /* 'BrtACEnd' */ break;

			case 0x0010: /* 'BrtFRTArchID$' */ break;

			default:
				if((R_n||"").indexOf("Begin") > 0){/* empty */}
				else if((R_n||"").indexOf("End") > 0){/* empty */}
				else if(!pass || opts.WTF) throw new Error("Unexpected record " + RT + " " + R_n);
		}
	}, opts);

	parse_wb_defaults(wb);

	// $FlowIgnore
	wb.Names = Names;

	return wb;
}

/* [MS-XLSB] 2.1.7.60 Workbook */
function write_BUNDLESHS(ba, wb, opts) {
	write_record(ba, "BrtBeginBundleShs");
	for(var idx = 0; idx != wb.SheetNames.length; ++idx) {
		var viz = wb.Workbook && wb.Workbook.Sheets && wb.Workbook.Sheets[idx] && wb.Workbook.Sheets[idx].Hidden || 0;
		var d = { Hidden: viz, iTabID: idx+1, strRelID: 'rId' + (idx+1), name: wb.SheetNames[idx] };
		write_record(ba, "BrtBundleSh", write_BrtBundleSh(d));
	}
	write_record(ba, "BrtEndBundleShs");
}

/* [MS-XLSB] 2.4.643 BrtFileVersion */
function write_BrtFileVersion(data, o) {
	if(!o) o = new_buf(127);
	for(var i = 0; i != 4; ++i) o.write_shift(4, 0);
	write_XLWideString("SheetJS", o);
	write_XLWideString(XLSX.version, o);
	write_XLWideString(XLSX.version, o);
	write_XLWideString("7262", o);
	o.length = o.l;
	return o.length > o.l ? o.slice(0, o.l) : o;
}

/* [MS-XLSB] 2.4.298 BrtBookView */
function write_BrtBookView(idx, o) {
	if(!o) o = new_buf(29);
	o.write_shift(-4, 0);
	o.write_shift(-4, 460);
	o.write_shift(4,  28800);
	o.write_shift(4,  17600);
	o.write_shift(4,  500);
	o.write_shift(4,  idx);
	o.write_shift(4,  idx);
	var flags = 0x78;
	o.write_shift(1,  flags);
	return o.length > o.l ? o.slice(0, o.l) : o;
}

/* [MS-XLSB] 2.1.7.60 Workbook */
function write_BOOKVIEWS(ba, wb, opts) {
	/* required if hidden tab appears before visible tab */
	if(!wb.Workbook || !wb.Workbook.Sheets) return;
	var sheets = wb.Workbook.Sheets;
	var i = 0, vistab = -1, hidden = -1;
	for(; i < sheets.length; ++i) {
		if(!sheets[i] || !sheets[i].Hidden && vistab == -1) vistab = i;
		else if(sheets[i].Hidden == 1 && hidden == -1) hidden = i;
	}
	if(hidden > vistab) return;
	write_record(ba, "BrtBeginBookViews");
	write_record(ba, "BrtBookView", write_BrtBookView(vistab));
	/* 1*(BrtBookView *FRT) */
	write_record(ba, "BrtEndBookViews");
}

/* [MS-XLSB] 2.4.302 BrtCalcProp */
function write_BrtCalcProp(data, o) {
	if(!o) o = new_buf(26);
	o.write_shift(4,0); /* force recalc */
	o.write_shift(4,1);
	o.write_shift(4,0);
	write_Xnum(0, o);
	o.write_shift(-4, 1023);
	o.write_shift(1, 0x33);
	o.write_shift(1, 0x00);
	return o;
}

/* [MS-XLSB] 2.4.640 BrtFileRecover */
function write_BrtFileRecover(data, o) {
	if(!o) o = new_buf(1);
	o.write_shift(1,0);
	return o;
}

/* [MS-XLSB] 2.1.7.60 Workbook */
function write_wb_bin(wb, opts) {
	var ba = buf_array();
	write_record(ba, "BrtBeginBook");
	write_record(ba, "BrtFileVersion", write_BrtFileVersion());
	/* [[BrtFileSharingIso] BrtFileSharing] */
	write_record(ba, "BrtWbProp", write_BrtWbProp());
	/* [ACABSPATH] */
	/* [[BrtBookProtectionIso] BrtBookProtection] */
	write_BOOKVIEWS(ba, wb, opts);
	write_BUNDLESHS(ba, wb, opts);
	/* [FNGROUP] */
	/* [EXTERNALS] */
	/* *BrtName */
	/* write_record(ba, "BrtCalcProp", write_BrtCalcProp()); */
	/* [BrtOleSize] */
	/* *(BrtUserBookView *FRT) */
	/* [PIVOTCACHEIDS] */
	/* [BrtWbFactoid] */
	/* [SMARTTAGTYPES] */
	/* [BrtWebOpt] */
	/* write_record(ba, "BrtFileRecover", write_BrtFileRecover()); */
	/* [WEBPUBITEMS] */
	/* [CRERRS] */
	/* FRTWORKBOOK */
	write_record(ba, "BrtEndBook");

	return ba.end();
}
function parse_wb(data, name, opts) {
	if(name.slice(-4)===".bin") return parse_wb_bin((data), opts);
	return parse_wb_xml((data), opts);
}

function parse_ws(data, name, opts, rels, wb, themes, styles) {
	if(name.slice(-4)===".bin") return parse_ws_bin((data), opts, rels, wb, themes, styles);
	return parse_ws_xml((data), opts, rels, wb, themes, styles);
}

function parse_cs(data, name, opts, rels, wb, themes, styles) {
	if(name.slice(-4)===".bin") return parse_cs_bin((data), opts, rels, wb, themes, styles);
	return parse_cs_xml((data), opts, rels, wb, themes, styles);
}

function parse_ms(data, name, opts, rels, wb, themes, styles) {
	if(name.slice(-4)===".bin") return parse_ms_bin((data), opts, rels, wb, themes, styles);
	return parse_ms_xml((data), opts, rels, wb, themes, styles);
}

function parse_ds(data, name, opts, rels, wb, themes, styles) {
	if(name.slice(-4)===".bin") return parse_ds_bin((data), opts, rels, wb, themes, styles);
	return parse_ds_xml((data), opts, rels, wb, themes, styles);
}

function parse_sty(data, name, themes, opts) {
	if(name.slice(-4)===".bin") return parse_sty_bin((data), themes, opts);
	return parse_sty_xml((data), themes, opts);
}

function parse_theme(data, name, opts) {
	return parse_theme_xml(data, opts);
}

function parse_sst(data, name, opts) {
	if(name.slice(-4)===".bin") return parse_sst_bin((data), opts);
	return parse_sst_xml((data), opts);
}

function parse_cmnt(data, name, opts) {
	if(name.slice(-4)===".bin") return parse_comments_bin((data), opts);
	return parse_comments_xml((data), opts);
}

function parse_cc(data, name, opts) {
	if(name.slice(-4)===".bin") return parse_cc_bin((data), opts);
	return parse_cc_xml((data), opts);
}

function write_wb(wb, name, opts) {
	return (name.slice(-4)===".bin" ? write_wb_bin : write_wb_xml)(wb, opts);
}

function write_ws(data, name, opts, wb, rels) {
	return (name.slice(-4)===".bin" ? write_ws_bin : write_ws_xml)(data, opts, wb, rels);
}

function write_cs(data, name, opts, wb, rels) {
	return (name.slice(-4)===".bin" ? write_cs_bin : write_cs_xml)(data, opts, wb, rels);
}

function write_sty(data, name, opts) {
	return (name.slice(-4)===".bin" ? write_sty_bin : write_sty_xml)(data, opts);
}

function write_sst(data, name, opts) {
	return (name.slice(-4)===".bin" ? write_sst_bin : write_sst_xml)(data, opts);
}

function write_cmnt(data, name, opts) {
	return (name.slice(-4)===".bin" ? write_comments_bin : write_comments_xml)(data, opts);
}
/*
function write_cc(data, name:string, opts) {
	return (name.slice(-4)===".bin" ? write_cc_bin : write_cc_xml)(data, opts);
}
*/
var attregexg2=/([\w:]+)=((?:")([^"]*)(?:")|(?:')([^']*)(?:'))/g;
var attregex2=/([\w:]+)=((?:")(?:[^"]*)(?:")|(?:')(?:[^']*)(?:'))/;
var _chr = function(c) { return String.fromCharCode(c); };
function xlml_parsexmltag(tag, skip_root) {
	var words = tag.split(/\s+/);
	var z = ([]); if(!skip_root) z[0] = words[0];
	if(words.length === 1) return z;
	var m = tag.match(attregexg2), y, j, w, i;
	if(m) for(i = 0; i != m.length; ++i) {
		y = m[i].match(attregex2);
if((j=y[1].indexOf(":")) === -1) z[y[1]] = y[2].substr(1,y[2].length-2);
		else {
			if(y[1].substr(0,6) === "xmlns:") w = "xmlns"+y[1].substr(6);
			else w = y[1].substr(j+1);
			z[w] = y[2].substr(1,y[2].length-2);
		}
	}
	return z;
}
function xlml_parsexmltagobj(tag) {
	var words = tag.split(/\s+/);
	var z = {};
	if(words.length === 1) return z;
	var m = tag.match(attregexg2), y, j, w, i;
	if(m) for(i = 0; i != m.length; ++i) {
		y = m[i].match(attregex2);
if((j=y[1].indexOf(":")) === -1) z[y[1]] = y[2].substr(1,y[2].length-2);
		else {
			if(y[1].substr(0,6) === "xmlns:") w = "xmlns"+y[1].substr(6);
			else w = y[1].substr(j+1);
			z[w] = y[2].substr(1,y[2].length-2);
		}
	}
	return z;
}

// ----

function xlml_format(format, value) {
	var fmt = XLMLFormatMap[format] || unescapexml(format);
	if(fmt === "General") return SSF._general(value);
	return SSF.format(fmt, value);
}

function xlml_set_custprop(Custprops, Rn, cp, val) {
	var oval = val;
	switch((cp[0].match(/dt:dt="([\w.]+)"/)||["",""])[1]) {
		case "boolean": oval = parsexmlbool(val); break;
		case "i2": case "int": oval = parseInt(val, 10); break;
		case "r4": case "float": oval = parseFloat(val); break;
		case "date": case "dateTime.tz": oval = parseDate(val); break;
		case "i8": case "string": case "fixed": case "uuid": case "bin.base64": break;
		default: throw new Error("bad custprop:" + cp[0]);
	}
	Custprops[unescapexml(Rn[3])] = oval;
}

function safe_format_xlml(cell, nf, o) {
	if(cell.t === 'z') return;
	if(!o || o.cellText !== false) try {
		if(cell.t === 'e') { cell.w = cell.w || BErr[cell.v]; }
		else if(nf === "General") {
			if(cell.t === 'n') {
				if((cell.v|0) === cell.v) cell.w = SSF._general_int(cell.v);
				else cell.w = SSF._general_num(cell.v);
			}
			else cell.w = SSF._general(cell.v);
		}
		else cell.w = xlml_format(nf||"General", cell.v);
	} catch(e) { if(o.WTF) throw e; }
	try {
		var z = XLMLFormatMap[nf]||nf||"General";
		if(o.cellNF) cell.z = z;
		if(o.cellDates && cell.t == 'n' && SSF.is_date(z)) {
			var _d = SSF.parse_date_code(cell.v); if(_d) { cell.t = 'd'; cell.v = new Date(Date.UTC(_d.y, _d.m-1,_d.d,_d.H,_d.M,_d.S,_d.u)); }
		}
	} catch(e) { if(o.WTF) throw e; }
}

function process_style_xlml(styles, stag, opts) {
	if(opts.cellStyles) {
		if(stag.Interior) {
			var I = stag.Interior;
			if(I.Pattern) I.patternType = XLMLPatternTypeMap[I.Pattern] || I.Pattern;
		}
	}
	styles[stag.ID] = stag;
}

/* TODO: there must exist some form of OSP-blessed spec */
function parse_xlml_data(xml, ss, data, cell, base, styles, csty, row, arrayf, o) {
	var nf = "General", sid = cell.StyleID, S = {}; o = o || {};
	var interiors = [];
	var i = 0;
	if(sid === undefined && row) sid = row.StyleID;
	if(sid === undefined && csty) sid = csty.StyleID;
	while(styles[sid] !== undefined) {
		if(styles[sid].nf) nf = styles[sid].nf;
		if(styles[sid].Interior) interiors.push(styles[sid].Interior);
		if(!styles[sid].Parent) break;
		sid = styles[sid].Parent;
	}
	switch(data.Type) {
		case 'Boolean':
			cell.t = 'b';
			cell.v = parsexmlbool(xml);
			break;
		case 'String':
			cell.t = 's'; cell.r = xlml_fixstr(unescapexml(xml));
			cell.v = xml.indexOf("<") > -1 ? unescapexml(ss) : cell.r;
			break;
		case 'DateTime':
			if(xml.slice(-1) != "Z") xml += "Z";
			cell.v = (parseDate(xml) - new Date(Date.UTC(1899, 11, 30))) / (24 * 60 * 60 * 1000);
			if(cell.v !== cell.v) cell.v = unescapexml(xml);
			else if(cell.v<60) cell.v = cell.v -1;
			if(!nf || nf == "General") nf = "yyyy-mm-dd";
			/* falls through */
		case 'Number':
			if(cell.v === undefined) cell.v=+xml;
			if(!cell.t) cell.t = 'n';
			break;
		case 'Error': cell.t = 'e'; cell.v = RBErr[xml]; if(o.cellText !== false) cell.w = xml; break;
		default: cell.t = 's'; cell.v = xlml_fixstr(ss||xml); break;
	}
	safe_format_xlml(cell, nf, o);
	if(o.cellFormula !== false) {
		if(cell.Formula) {
			var fstr = unescapexml(cell.Formula);
			/* strictly speaking, the leading = is required but some writers omit */
			if(fstr.charCodeAt(0) == 61 /* = */) fstr = fstr.substr(1);
			cell.f = rc_to_a1(fstr, base);
			delete cell.Formula;
			if(cell.ArrayRange == "RC") cell.F = rc_to_a1("RC:RC", base);
			else if(cell.ArrayRange) {
				cell.F = rc_to_a1(cell.ArrayRange, base);
				arrayf.push([safe_decode_range(cell.F), cell.F]);
			}
		} else {
			for(i = 0; i < arrayf.length; ++i)
				if(base.r >= arrayf[i][0].s.r && base.r <= arrayf[i][0].e.r)
					if(base.c >= arrayf[i][0].s.c && base.c <= arrayf[i][0].e.c)
						cell.F = arrayf[i][1];
		}
	}
	if(o.cellStyles) {
		interiors.forEach(function(x) {
			if(!S.patternType && x.patternType) S.patternType = x.patternType;
		});
		cell.s = S;
	}
	cell.ixfe = cell.StyleID !== undefined ? cell.StyleID : 'Default';
}

function xlml_clean_comment(comment) {
	comment.t = comment.v || "";
	comment.t = comment.t.replace(/\r\n/g,"\n").replace(/\r/g,"\n");
	comment.v = comment.w = comment.ixfe = undefined;
}

function xlml_normalize(d) {
	if(has_buf && Buffer.isBuffer(d)) return d.toString('utf8');
	if(typeof d === 'string') return d;
	throw new Error("Bad input format: expected Buffer or string");
}

/* TODO: Everything */
/* UOS uses CJK in tags */
var xlmlregex = /<(\/?)([^\s?>!\/:]*:|)([^\s?>]*[^\s?>\/])[^>]*>/mg;
//var xlmlregex = /<(\/?)([a-z0-9]*:|)(\w+)[^>]*>/mg;
function parse_xlml_xml(d, opts) {
	make_ssf(SSF);
	var str = debom(xlml_normalize(d));
	if(opts && opts.type == 'binary' && typeof cptable !== 'undefined') str = cptable.utils.decode(65001, char_codes(str));
	if(str.substr(0,1000).indexOf("<html") >= 0) return HTML_.to_workbook(str, opts);
	var Rn;
	var state = [], tmp;
	if(DENSE != null && opts.dense == null) opts.dense = DENSE;
	var sheets = {}, sheetnames = [], cursheet = (opts.dense ? [] : {}), sheetname = "";
	var table = {}, cell = ({}), row = {};
	var dtag = xlml_parsexmltag('<Data ss:Type="String">'), didx = 0;
	var c = 0, r = 0;
	var refguess = {s: {r:2000000, c:2000000}, e: {r:0, c:0} };
	var styles = {}, stag = {};
	var ss = "", fidx = 0;
	var mergecells = [];
	var Props = {}, Custprops = {}, pidx = 0, cp = {};
	var comments = [], comment = {};
	var cstys = [], csty, seencol = false;
	var arrayf = [];
	var rowinfo = [], rowobj = {};
	var Workbook = { Sheets:[] }, wsprops = {};
	xlmlregex.lastIndex = 0;
	str = str.replace(/<!--([^\u2603]*?)-->/mg,"");
	while((Rn = xlmlregex.exec(str))) switch(Rn[3]) {
		case 'Data':
			if(state[state.length-1][1]) break;
			if(Rn[1]==='/') parse_xlml_data(str.slice(didx, Rn.index), ss, dtag, state[state.length-1][0]=="Comment"?comment:cell, {c:c,r:r}, styles, cstys[c], row, arrayf, opts);
			else { ss = ""; dtag = xlml_parsexmltag(Rn[0]); didx = Rn.index + Rn[0].length; }
			break;
		case 'Cell':
			if(Rn[1]==='/'){
				if(comments.length > 0) cell.c = comments;
				if((!opts.sheetRows || opts.sheetRows > r) && cell.v !== undefined) {
					if(opts.dense) {
						if(!cursheet[r]) cursheet[r] = [];
						cursheet[r][c] = cell;
					} else cursheet[encode_col(c) + encode_row(r)] = cell;
				}
				if(cell.HRef) {
					cell.l = {Target:cell.HRef, Tooltip:cell.HRefScreenTip};
					delete cell.HRef; delete cell.HRefScreenTip;
				}
				if(cell.MergeAcross || cell.MergeDown) {
					var cc = c + (parseInt(cell.MergeAcross,10)|0);
					var rr = r + (parseInt(cell.MergeDown,10)|0);
					mergecells.push({s:{c:c,r:r},e:{c:cc,r:rr}});
				}
				if(!opts.sheetStubs) { if(cell.MergeAcross) c = cc + 1; else ++c; }
				else if(cell.MergeAcross || cell.MergeDown) {
for(var cma = c; cma <= cc; ++cma) {
						for(var cmd = r; cmd <= rr; ++cmd) {
							if(cma > c || cmd > r) {
								if(opts.dense) {
									if(!cursheet[cmd]) cursheet[cmd] = [];
									cursheet[cmd][cma] = {t:'z'};
								} else cursheet[encode_col(cma) + encode_row(cmd)] = {t:'z'};
							}
						}
					}
					c = cc + 1;
				}
				else ++c;
			} else {
				cell = xlml_parsexmltagobj(Rn[0]);
				if(cell.Index) c = +cell.Index - 1;
				if(c < refguess.s.c) refguess.s.c = c;
				if(c > refguess.e.c) refguess.e.c = c;
				if(Rn[0].slice(-2) === "/>") ++c;
				comments = [];
			}
			break;
		case 'Row':
			if(Rn[1]==='/' || Rn[0].slice(-2) === "/>") {
				if(r < refguess.s.r) refguess.s.r = r;
				if(r > refguess.e.r) refguess.e.r = r;
				if(Rn[0].slice(-2) === "/>") {
					row = xlml_parsexmltag(Rn[0]);
					if(row.Index) r = +row.Index - 1;
				}
				c = 0; ++r;
			} else {
				row = xlml_parsexmltag(Rn[0]);
				if(row.Index) r = +row.Index - 1;
				rowobj = {};
				if(row.AutoFitHeight == "0") {
					rowobj.hpx = parseInt(row.Height, 10); rowobj.hpt = px2pt(rowobj.hpx);
					rowinfo[r] = rowobj;
				}
				if(row.Hidden == "1") { rowobj.hidden = true; rowinfo[r] = rowobj; }
			}
			break;
		case 'Worksheet': /* TODO: read range from FullRows/FullColumns */
			if(Rn[1]==='/'){
				if((tmp=state.pop())[0]!==Rn[3]) throw new Error("Bad state: "+tmp.join("|"));
				sheetnames.push(sheetname);
				if(refguess.s.r <= refguess.e.r && refguess.s.c <= refguess.e.c) cursheet["!ref"] = encode_range(refguess);
				if(mergecells.length) cursheet["!merges"] = mergecells;
				if(cstys.length > 0) cursheet["!cols"] = cstys;
				if(rowinfo.length > 0) cursheet["!rows"] = rowinfo;
				sheets[sheetname] = cursheet;
			} else {
				refguess = {s: {r:2000000, c:2000000}, e: {r:0, c:0} };
				r = c = 0;
				state.push([Rn[3], false]);
				tmp = xlml_parsexmltag(Rn[0]);
				sheetname = unescapexml(tmp.Name);
				cursheet = (opts.dense ? [] : {});
				mergecells = [];
				arrayf = [];
				rowinfo = [];
				wsprops = {name:sheetname, Hidden:0};
				Workbook.Sheets.push(wsprops);
			}
			break;
		case 'Table':
			if(Rn[1]==='/'){if((tmp=state.pop())[0]!==Rn[3]) throw new Error("Bad state: "+tmp.join("|"));}
			else if(Rn[0].slice(-2) == "/>") break;
			else {
				table = xlml_parsexmltag(Rn[0]);
				state.push([Rn[3], false]);
				cstys = []; seencol = false;
			}
			break;

		case 'Style':
			if(Rn[1]==='/') process_style_xlml(styles, stag, opts);
			else stag = xlml_parsexmltag(Rn[0]);
			break;

		case 'NumberFormat':
			stag.nf = unescapexml(xlml_parsexmltag(Rn[0]).Format || "General");
			if(XLMLFormatMap[stag.nf]) stag.nf = XLMLFormatMap[stag.nf];
			for(var ssfidx = 0; ssfidx != 0x188; ++ssfidx) if(SSF._table[ssfidx] == stag.nf) break;
			if(ssfidx == 0x188) for(ssfidx = 0x39; ssfidx != 0x188; ++ssfidx) if(SSF._table[ssfidx] == null) { SSF.load(stag.nf, ssfidx); break; }
			break;

		case 'Column':
			if(state[state.length-1][0] !== 'Table') break;
			csty = xlml_parsexmltag(Rn[0]);
			if(csty.Hidden) { csty.hidden = true; delete csty.Hidden; }
			if(csty.Width) csty.wpx = parseInt(csty.Width, 10);
			if(!seencol && csty.wpx > 10) {
				seencol = true; MDW = DEF_MDW; //find_mdw_wpx(csty.wpx);
				for(var _col = 0; _col < cstys.length; ++_col) if(cstys[_col]) process_col(cstys[_col]);
			}
			if(seencol) process_col(csty);
			cstys[(csty.Index-1||cstys.length)] = csty;
			for(var i = 0; i < +csty.Span; ++i) cstys[cstys.length] = dup(csty);
			break;

		case 'NamedRange':
			if(!Workbook.Names) Workbook.Names = [];
			var _NamedRange = parsexmltag(Rn[0]);
			var _DefinedName = ({
				Name: _NamedRange.Name,
				Ref: rc_to_a1(_NamedRange.RefersTo.substr(1))
			});
			if(Workbook.Sheets.length>0) _DefinedName.Sheet=Workbook.Sheets.length-1;
Workbook.Names.push(_DefinedName);
			break;

		case 'NamedCell': break;
		case 'B': break;
		case 'I': break;
		case 'U': break;
		case 'S': break;
		case 'Sub': break;
		case 'Sup': break;
		case 'Span': break;
		case 'Border': break;
		case 'Alignment': break;
		case 'Borders': break;
		case 'Font':
			if(Rn[0].slice(-2) === "/>") break;
			else if(Rn[1]==="/") ss += str.slice(fidx, Rn.index);
			else fidx = Rn.index + Rn[0].length;
			break;
		case 'Interior':
			if(!opts.cellStyles) break;
			stag.Interior = xlml_parsexmltag(Rn[0]);
			break;
		case 'Protection': break;

		case 'Author':
		case 'Title':
		case 'Description':
		case 'Created':
		case 'Keywords':
		case 'Subject':
		case 'Category':
		case 'Company':
		case 'LastAuthor':
		case 'LastSaved':
		case 'LastPrinted':
		case 'Version':
		case 'Revision':
		case 'TotalTime':
		case 'HyperlinkBase':
		case 'Manager':
		case 'ContentStatus':
		case 'Identifier':
		case 'Language':
			if(Rn[0].slice(-2) === "/>") break;
			else if(Rn[1]==="/") xlml_set_prop(Props, Rn[3], str.slice(pidx, Rn.index));
			else pidx = Rn.index + Rn[0].length;
			break;
		case 'Paragraphs': break;

		case 'Styles':
		case 'Workbook':
			if(Rn[1]==='/'){if((tmp=state.pop())[0]!==Rn[3]) throw new Error("Bad state: "+tmp.join("|"));}
			else state.push([Rn[3], false]);
			break;

		case 'Comment':
			if(Rn[1]==='/'){
				if((tmp=state.pop())[0]!==Rn[3]) throw new Error("Bad state: "+tmp.join("|"));
				xlml_clean_comment(comment);
				comments.push(comment);
			} else {
				state.push([Rn[3], false]);
				tmp = xlml_parsexmltag(Rn[0]);
				comment = {a:tmp.Author};
			}
			break;

		case 'AutoFilter':
			if(Rn[1]==='/'){if((tmp=state.pop())[0]!==Rn[3]) throw new Error("Bad state: "+tmp.join("|"));}
			else if(Rn[0].charAt(Rn[0].length-2) !== '/') {
				var AutoFilter = xlml_parsexmltag(Rn[0]);
				cursheet['!autofilter'] = { ref:rc_to_a1(AutoFilter.Range).replace(/\$/g,"") };
				state.push([Rn[3], true]);
			}
			break;

		case 'Name': break;

		case 'ComponentOptions':
		case 'DocumentProperties':
		case 'CustomDocumentProperties':
		case 'OfficeDocumentSettings':
		case 'PivotTable':
		case 'PivotCache':
		case 'Names':
		case 'MapInfo':
		case 'PageBreaks':
		case 'QueryTable':
		case 'DataValidation':
		case 'Sorting':
		case 'Schema':
		case 'data':
		case 'ConditionalFormatting':
		case 'SmartTagType':
		case 'SmartTags':
		case 'ExcelWorkbook':
		case 'WorkbookOptions':
		case 'WorksheetOptions':
			if(Rn[1]==='/'){if((tmp=state.pop())[0]!==Rn[3]) throw new Error("Bad state: "+tmp.join("|"));}
			else if(Rn[0].charAt(Rn[0].length-2) !== '/') state.push([Rn[3], true]);
			break;

		default:
			/* FODS file root is <office:document> */
			if(state.length == 0 && Rn[3] == "document") return parse_fods(str, opts);
			/* UOS file root is <uof:UOF> */
			if(state.length == 0 && Rn[3] == "UOF") return parse_fods(str, opts);

			var seen = true;
			switch(state[state.length-1][0]) {
				/* OfficeDocumentSettings */
				case 'OfficeDocumentSettings': switch(Rn[3]) {
					case 'AllowPNG': break;
					case 'RemovePersonalInformation': break;
					case 'DownloadComponents': break;
					case 'LocationOfComponents': break;
					case 'Colors': break;
					case 'Color': break;
					case 'Index': break;
					case 'RGB': break;
					case 'PixelsPerInch': break; // TODO: set PPI
					case 'TargetScreenSize': break;
					case 'ReadOnlyRecommended': break;
					default: seen = false;
				} break;

				/* ComponentOptions */
				case 'ComponentOptions': switch(Rn[3]) {
					case 'Toolbar': break;
					case 'HideOfficeLogo': break;
					case 'SpreadsheetAutoFit': break;
					case 'Label': break;
					case 'Caption': break;
					case 'MaxHeight': break;
					case 'MaxWidth': break;
					case 'NextSheetNumber': break;
					default: seen = false;
				} break;

				/* ExcelWorkbook */
				case 'ExcelWorkbook': switch(Rn[3]) {
					case 'WindowHeight': break;
					case 'WindowWidth': break;
					case 'WindowTopX': break;
					case 'WindowTopY': break;
					case 'TabRatio': break;
					case 'ProtectStructure': break;
					case 'ProtectWindows': break;
					case 'ActiveSheet': break;
					case 'DisplayInkNotes': break;
					case 'FirstVisibleSheet': break;
					case 'SupBook': break;
					case 'SheetName': break;
					case 'SheetIndex': break;
					case 'SheetIndexFirst': break;
					case 'SheetIndexLast': break;
					case 'Dll': break;
					case 'AcceptLabelsInFormulas': break;
					case 'DoNotSaveLinkValues': break;
					case 'Date1904': break;
					case 'Iteration': break;
					case 'MaxIterations': break;
					case 'MaxChange': break;
					case 'Path': break;
					case 'Xct': break;
					case 'Count': break;
					case 'SelectedSheets': break;
					case 'Calculation': break;
					case 'Uncalced': break;
					case 'StartupPrompt': break;
					case 'Crn': break;
					case 'ExternName': break;
					case 'Formula': break;
					case 'ColFirst': break;
					case 'ColLast': break;
					case 'WantAdvise': break;
					case 'Boolean': break;
					case 'Error': break;
					case 'Text': break;
					case 'OLE': break;
					case 'NoAutoRecover': break;
					case 'PublishObjects': break;
					case 'DoNotCalculateBeforeSave': break;
					case 'Number': break;
					case 'RefModeR1C1': break;
					case 'EmbedSaveSmartTags': break;
					default: seen = false;
				} break;

				/* WorkbookOptions */
				case 'WorkbookOptions': switch(Rn[3]) {
					case 'OWCVersion': break;
					case 'Height': break;
					case 'Width': break;
					default: seen = false;
				} break;

				/* WorksheetOptions */
				case 'WorksheetOptions': switch(Rn[3]) {
					case 'Visible':
						if(Rn[0].slice(-2) === "/>"){/* empty */}
						else if(Rn[1]==="/") switch(str.slice(pidx, Rn.index)) {
							case "SheetHidden": wsprops.Hidden = 1; break;
							case "SheetVeryHidden": wsprops.Hidden = 2; break;
						}
						else pidx = Rn.index + Rn[0].length;
						break;
					case 'Header':
						if(!cursheet['!margins']) default_margins(cursheet['!margins']={}, 'xlml');
						cursheet['!margins'].header = parsexmltag(Rn[0]).Margin;
						break;
					case 'Footer':
						if(!cursheet['!margins']) default_margins(cursheet['!margins']={}, 'xlml');
						cursheet['!margins'].footer = parsexmltag(Rn[0]).Margin;
						break;
					case 'PageMargins':
						var pagemargins = parsexmltag(Rn[0]);
						if(!cursheet['!margins']) default_margins(cursheet['!margins']={},'xlml');
						if(pagemargins.Top) cursheet['!margins'].top = pagemargins.Top;
						if(pagemargins.Left) cursheet['!margins'].left = pagemargins.Left;
						if(pagemargins.Right) cursheet['!margins'].right = pagemargins.Right;
						if(pagemargins.Bottom) cursheet['!margins'].bottom = pagemargins.Bottom;
						break;
					case 'Unsynced': break;
					case 'Print': break;
					case 'Panes': break;
					case 'Scale': break;
					case 'Pane': break;
					case 'Number': break;
					case 'Layout': break;
					case 'PageSetup': break;
					case 'Selected': break;
					case 'ProtectObjects': break;
					case 'EnableSelection': break;
					case 'ProtectScenarios': break;
					case 'ValidPrinterInfo': break;
					case 'HorizontalResolution': break;
					case 'VerticalResolution': break;
					case 'NumberofCopies': break;
					case 'ActiveRow': break;
					case 'ActiveCol': break;
					case 'ActivePane': break;
					case 'TopRowVisible': break;
					case 'TopRowBottomPane': break;
					case 'LeftColumnVisible': break;
					case 'LeftColumnRightPane': break;
					case 'FitToPage': break;
					case 'RangeSelection': break;
					case 'PaperSizeIndex': break;
					case 'PageLayoutZoom': break;
					case 'PageBreakZoom': break;
					case 'FilterOn': break;
					case 'DoNotDisplayGridlines': break;
					case 'SplitHorizontal': break;
					case 'SplitVertical': break;
					case 'FreezePanes': break;
					case 'FrozenNoSplit': break;
					case 'FitWidth': break;
					case 'FitHeight': break;
					case 'CommentsLayout': break;
					case 'Zoom': break;
					case 'LeftToRight': break;
					case 'Gridlines': break;
					case 'AllowSort': break;
					case 'AllowFilter': break;
					case 'AllowInsertRows': break;
					case 'AllowDeleteRows': break;
					case 'AllowInsertCols': break;
					case 'AllowDeleteCols': break;
					case 'AllowInsertHyperlinks': break;
					case 'AllowFormatCells': break;
					case 'AllowSizeCols': break;
					case 'AllowSizeRows': break;
					case 'NoSummaryRowsBelowDetail': break;
					case 'TabColorIndex': break;
					case 'DoNotDisplayHeadings': break;
					case 'ShowPageLayoutZoom': break;
					case 'NoSummaryColumnsRightDetail': break;
					case 'BlackAndWhite': break;
					case 'DoNotDisplayZeros': break;
					case 'DisplayPageBreak': break;
					case 'RowColHeadings': break;
					case 'DoNotDisplayOutline': break;
					case 'NoOrientation': break;
					case 'AllowUsePivotTables': break;
					case 'ZeroHeight': break;
					case 'ViewableRange': break;
					case 'Selection': break;
					case 'ProtectContents': break;
					default: seen = false;
				} break;

				/* PivotTable */
				case 'PivotTable': case 'PivotCache': switch(Rn[3]) {
					case 'ImmediateItemsOnDrop': break;
					case 'ShowPageMultipleItemLabel': break;
					case 'CompactRowIndent': break;
					case 'Location': break;
					case 'PivotField': break;
					case 'Orientation': break;
					case 'LayoutForm': break;
					case 'LayoutSubtotalLocation': break;
					case 'LayoutCompactRow': break;
					case 'Position': break;
					case 'PivotItem': break;
					case 'DataType': break;
					case 'DataField': break;
					case 'SourceName': break;
					case 'ParentField': break;
					case 'PTLineItems': break;
					case 'PTLineItem': break;
					case 'CountOfSameItems': break;
					case 'Item': break;
					case 'ItemType': break;
					case 'PTSource': break;
					case 'CacheIndex': break;
					case 'ConsolidationReference': break;
					case 'FileName': break;
					case 'Reference': break;
					case 'NoColumnGrand': break;
					case 'NoRowGrand': break;
					case 'BlankLineAfterItems': break;
					case 'Hidden': break;
					case 'Subtotal': break;
					case 'BaseField': break;
					case 'MapChildItems': break;
					case 'Function': break;
					case 'RefreshOnFileOpen': break;
					case 'PrintSetTitles': break;
					case 'MergeLabels': break;
					case 'DefaultVersion': break;
					case 'RefreshName': break;
					case 'RefreshDate': break;
					case 'RefreshDateCopy': break;
					case 'VersionLastRefresh': break;
					case 'VersionLastUpdate': break;
					case 'VersionUpdateableMin': break;
					case 'VersionRefreshableMin': break;
					case 'Calculation': break;
					default: seen = false;
				} break;

				/* PageBreaks */
				case 'PageBreaks': switch(Rn[3]) {
					case 'ColBreaks': break;
					case 'ColBreak': break;
					case 'RowBreaks': break;
					case 'RowBreak': break;
					case 'ColStart': break;
					case 'ColEnd': break;
					case 'RowEnd': break;
					default: seen = false;
				} break;

				/* AutoFilter */
				case 'AutoFilter': switch(Rn[3]) {
					case 'AutoFilterColumn': break;
					case 'AutoFilterCondition': break;
					case 'AutoFilterAnd': break;
					case 'AutoFilterOr': break;
					default: seen = false;
				} break;

				/* QueryTable */
				case 'QueryTable': switch(Rn[3]) {
					case 'Id': break;
					case 'AutoFormatFont': break;
					case 'AutoFormatPattern': break;
					case 'QuerySource': break;
					case 'QueryType': break;
					case 'EnableRedirections': break;
					case 'RefreshedInXl9': break;
					case 'URLString': break;
					case 'HTMLTables': break;
					case 'Connection': break;
					case 'CommandText': break;
					case 'RefreshInfo': break;
					case 'NoTitles': break;
					case 'NextId': break;
					case 'ColumnInfo': break;
					case 'OverwriteCells': break;
					case 'DoNotPromptForFile': break;
					case 'TextWizardSettings': break;
					case 'Source': break;
					case 'Number': break;
					case 'Decimal': break;
					case 'ThousandSeparator': break;
					case 'TrailingMinusNumbers': break;
					case 'FormatSettings': break;
					case 'FieldType': break;
					case 'Delimiters': break;
					case 'Tab': break;
					case 'Comma': break;
					case 'AutoFormatName': break;
					case 'VersionLastEdit': break;
					case 'VersionLastRefresh': break;
					default: seen = false;
				} break;

				case 'Sorting':
				case 'ConditionalFormatting':
				case 'DataValidation':
				switch(Rn[3]) {
					case 'Range': break;
					case 'Type': break;
					case 'Min': break;
					case 'Max': break;
					case 'Sort': break;
					case 'Descending': break;
					case 'Order': break;
					case 'CaseSensitive': break;
					case 'Value': break;
					case 'ErrorStyle': break;
					case 'ErrorMessage': break;
					case 'ErrorTitle': break;
					case 'CellRangeList': break;
					case 'InputMessage': break;
					case 'InputTitle': break;
					case 'ComboHide': break;
					case 'InputHide': break;
					case 'Condition': break;
					case 'Qualifier': break;
					case 'UseBlank': break;
					case 'Value1': break;
					case 'Value2': break;
					case 'Format': break;
					default: seen = false;
				} break;

				/* MapInfo (schema) */
				case 'MapInfo': case 'Schema': case 'data': switch(Rn[3]) {
					case 'Map': break;
					case 'Entry': break;
					case 'Range': break;
					case 'XPath': break;
					case 'Field': break;
					case 'XSDType': break;
					case 'FilterOn': break;
					case 'Aggregate': break;
					case 'ElementType': break;
					case 'AttributeType': break;
				/* These are from xsd (XML Schema Definition) */
					case 'schema':
					case 'element':
					case 'complexType':
					case 'datatype':
					case 'all':
					case 'attribute':
					case 'extends': break;

					case 'row': break;
					default: seen = false;
				} break;

				/* SmartTags (can be anything) */
				case 'SmartTags': break;

				default: seen = false; break;
			}
			if(seen) break;
			/* CustomDocumentProperties */
			if(!state[state.length-1][1]) throw 'Unrecognized tag: ' + Rn[3] + "|" + state.join("|");
			if(state[state.length-1][0]==='CustomDocumentProperties') {
				if(Rn[0].slice(-2) === "/>") break;
				else if(Rn[1]==="/") xlml_set_custprop(Custprops, Rn, cp, str.slice(pidx, Rn.index));
				else { cp = Rn; pidx = Rn.index + Rn[0].length; }
				break;
			}
			if(opts.WTF) throw 'Unrecognized tag: ' + Rn[3] + "|" + state.join("|");
	}
	var out = ({});
	if(!opts.bookSheets && !opts.bookProps) out.Sheets = sheets;
	out.SheetNames = sheetnames;
	out.Workbook = Workbook;
	out.SSF = SSF.get_table();
	out.Props = Props;
	out.Custprops = Custprops;
	return out;
}

function parse_xlml(data, opts) {
	fix_read_opts(opts=opts||{});
	switch(opts.type||"base64") {
		case "base64": return parse_xlml_xml(Base64.decode(data), opts);
		case "binary": case "buffer": case "file": return parse_xlml_xml(data, opts);
		case "array": return parse_xlml_xml(data.map(_chr).join(""), opts);
	}
}

/* TODO */
function write_props_xlml(wb, opts) {
	var o = [];
	/* DocumentProperties */
	if(wb.Props) o.push(xlml_write_docprops(wb.Props, opts));
	/* CustomDocumentProperties */
	if(wb.Custprops) o.push(xlml_write_custprops(wb.Props, wb.Custprops, opts));
	return o.join("");
}
/* TODO */
function write_wb_xlml(wb, opts) {
	/* OfficeDocumentSettings */
	/* ExcelWorkbook */
	return "";
}
/* TODO */
function write_sty_xlml(wb, opts) {
	/* Styles */
	return "";
}
/* WorksheetOptions */
function write_ws_xlml_wsopts(ws, opts, idx, wb) {
	if(!ws) return "";
	var o = [];
	/* NOTE: spec technically allows any order, but stick with implied order */

	/* FitToPage */
	/* DoNotDisplayColHeaders */
	/* DoNotDisplayRowHeaders */
	/* ViewableRange */
	/* Selection */
	/* GridlineColor */
	/* Name */
	/* ExcelWorksheetType */
	/* IntlMacro */
	/* Unsynced */
	/* Selected */
	/* CodeName */

	if(ws['!margins']) {
		o.push("<PageSetup>");
		if(ws['!margins'].header) o.push(writextag("Header", null, {'x:Margin':ws['!margins'].header}));
		if(ws['!margins'].footer) o.push(writextag("Footer", null, {'x:Margin':ws['!margins'].footer}));
		o.push(writextag("PageMargins", null, {
			'x:Bottom': ws['!margins'].bottom || "0.75",
			'x:Left': ws['!margins'].left || "0.7",
			'x:Right': ws['!margins'].right || "0.7",
			'x:Top': ws['!margins'].top || "0.75"
		}));
		o.push("</PageSetup>");
	}

	/* PageSetup */
	/* DisplayPageBreak */
	/* TransitionExpressionEvaluation */
	/* TransitionFormulaEntry */
	/* Print */
	/* Zoom */
	/* PageLayoutZoom */
	/* PageBreakZoom */
	/* ShowPageBreakZoom */
	/* DefaultRowHeight */
	/* DefaultColumnWidth */
	/* StandardWidth */

	if(wb && wb.Workbook && wb.Workbook.Sheets && wb.Workbook.Sheets[idx]) {
		/* Visible */
		if(wb.Workbook.Sheets[idx].Hidden) o.push(writextag("Visible", (wb.Workbook.Sheets[idx].Hidden == 1 ? "SheetHidden" : "SheetVeryHidden"), {}));
		else {
			/* Selected */
			for(var i = 0; i < idx; ++i) if(wb.Workbook.Sheets[i] && !wb.Workbook.Sheets[i].Hidden) break;
			if(i == idx) o.push("<Selected/>");
		}
	}

	/* LeftColumnVisible */
	/* DisplayRightToLeft */
	/* GridlineColorIndex */
	/* DisplayFormulas */
	/* DoNotDisplayGridlines */
	/* DoNotDisplayHeadings */
	/* DoNotDisplayOutline */
	/* ApplyAutomaticOutlineStyles */
	/* NoSummaryRowsBelowDetail */
	/* NoSummaryColumnsRightDetail */
	/* DoNotDisplayZeros */
	/* ActiveRow */
	/* ActiveColumn */
	/* FilterOn */
	/* RangeSelection */
	/* TopRowVisible */
	/* TopRowBottomPane */
	/* LeftColumnRightPane */
	/* ActivePane */
	/* SplitHorizontal */
	/* SplitVertical */
	/* FreezePanes */
	/* FrozenNoSplit */
	/* TabColorIndex */
	/* Panes */

	/* NOTE: Password not supported in XLML Format */
	if(ws['!protect']) {
		o.push(writetag("ProtectContents", "True"));
		if(ws['!protect'].objects) o.push(writetag("ProtectObjects", "True"));
		if(ws['!protect'].scenarios) o.push(writetag("ProtectScenarios", "True"));
		if(ws['!protect'].selectLockedCells != null && !ws['!protect'].selectLockedCells) o.push(writetag("EnableSelection", "NoSelection"));
		else if(ws['!protect'].selectUnlockedCells != null && !ws['!protect'].selectUnlockedCells) o.push(writetag("EnableSelection", "UnlockedCells"));
	[
		[ "formatColumns", "AllowFormatCells" ],
		[ "formatRows", "AllowSizeCols" ],
		[ "formatCells", "AllowSizeRows" ],
		[ "insertColumns", "AllowInsertCols" ],
		[ "insertRows", "AllowInsertRows" ],
		[ "insertHyperlinks", "AllowInsertHyperlinks" ],
		[ "deleteColumns", "AllowDeleteCols" ],
		[ "deleteRows", "AllowDeleteRows" ],
		[ "sort", "AllowSort" ],
		[ "autoFilter", "AllowFilter" ],
		[ "pivotTables", "AllowUsePivotTables" ]
	].forEach(function(x) { if(ws['!protect'][x[0]]) o.push("<"+x[1]+"/>"); });
	}

	if(o.length == 0) return "";
	return writextag("WorksheetOptions", o.join(""), {xmlns:XLMLNS.x});
}
function write_ws_xlml_comment(comments) {
	return comments.map(function(c) {
		// TODO: formatted text
		var t = xlml_unfixstr(c.t||"");
		var d =writextag("ss:Data", t, {"xmlns":"http://www.w3.org/TR/REC-html40"});
		return writextag("Comment", d, {"ss:Author":c.a});
	}).join("");
}
function write_ws_xlml_cell(cell, ref, ws, opts, idx, wb, addr){
	if(!cell || cell.v == undefined && cell.f == undefined) return "<Cell></Cell>";

	var attr = {};
	if(cell.f) attr["ss:Formula"] = "=" + escapexml(a1_to_rc(cell.f, addr));
	if(cell.F && cell.F.substr(0, ref.length) == ref) {
		var end = decode_cell(cell.F.substr(ref.length + 1));
		attr["ss:ArrayRange"] = "RC:R" + (end.r == addr.r ? "" : "[" + (end.r - addr.r) + "]") + "C" + (end.c == addr.c ? "" : "[" + (end.c - addr.c) + "]");
	}

	if(cell.l && cell.l.Target) {
		attr["ss:HRef"] = escapexml(cell.l.Target);
		if(cell.l.Tooltip) attr["x:HRefScreenTip"] = escapexml(cell.l.Tooltip);
	}

	if(ws['!merges']) {
		var marr = ws['!merges'];
		for(var mi = 0; mi != marr.length; ++mi) {
			if(marr[mi].s.c != addr.c || marr[mi].s.r != addr.r) continue;
			if(marr[mi].e.c > marr[mi].s.c) attr['ss:MergeAcross'] = marr[mi].e.c - marr[mi].s.c;
			if(marr[mi].e.r > marr[mi].s.r) attr['ss:MergeDown'] = marr[mi].e.r - marr[mi].s.r;
		}
	}

	var t = "", p = "";
	switch(cell.t) {
		case 'z': return "";
		case 'n': t = 'Number'; p = String(cell.v); break;
		case 'b': t = 'Boolean'; p = (cell.v ? "1" : "0"); break;
		case 'e': t = 'Error'; p = BErr[cell.v]; break;
		case 'd': t = 'DateTime'; p = new Date(cell.v).toISOString(); break;
		case 's': t = 'String'; p = escapexml(cell.v||""); break;
	}
	var _v = (cell.v != null ? p : "");
	if(opts && opts.type == 'binary' && typeof cptable !== 'undefined' && cell.t == 's') {
		_v = cptable.utils.encode(65001, _v);
		var __v = "";
		for(var __i = 0; __i < _v.length; ++__i) __v += String.fromCharCode(_v[__i]);
		_v = __v;
	}
	var m = '<Data ss:Type="' + t + '">' + _v + '</Data>';

	if((cell.c||[]).length > 0) m += write_ws_xlml_comment(cell.c);

	return writextag("Cell", m, attr);
}
function write_ws_xlml_row(R, row) {
	var o = '<Row ss:Index="' + (R+1) + '"';
	if(row) {
		if(row.hpt && !row.hpx) row.hpx = pt2px(row.hpt);
		if(row.hpx) o += ' ss:AutoFitHeight="0" ss:Height="' + row.hpx + '"';
		if(row.hidden) o += ' ss:Hidden="1"';
	}
	return o + '>';
}
/* TODO */
function write_ws_xlml_table(ws, opts, idx, wb) {
	if(!ws['!ref']) return "";
	var range = safe_decode_range(ws['!ref']);
	var marr = ws['!merges'] || [], mi = 0;
	var o = [];
	if(ws['!cols']) ws['!cols'].forEach(function(n, i) {
		process_col(n);
		var w = !!n.width;
		var p = col_obj_w(i, n);
		var k = {"ss:Index":i+1};
		if(w) k['ss:Width'] = width2px(p.width);
		if(n.hidden) k['ss:Hidden']="1";
		o.push(writextag("Column",null,k));
	});
	var dense = Array.isArray(ws);
	for(var R = range.s.r; R <= range.e.r; ++R) {
		var row = [write_ws_xlml_row(R, (ws['!rows']||[])[R])];
		for(var C = range.s.c; C <= range.e.c; ++C) {
			var skip = false;
			for(mi = 0; mi != marr.length; ++mi) {
				if(marr[mi].s.c > C) continue;
				if(marr[mi].s.r > R) continue;
				if(marr[mi].e.c < C) continue;
				if(marr[mi].e.r < R) continue;
				if(marr[mi].s.c != C || marr[mi].s.r != R) skip = true;
				break;
			}
			if(skip) continue;
			var addr = {r:R,c:C};
			var ref = encode_cell(addr), cell = dense ? (ws[R]||[])[C] : ws[ref];
			row.push(write_ws_xlml_cell(cell, ref, ws, opts, idx, wb, addr));
		}
		row.push("</Row>");
		if(row.length > 2) o.push(row.join(""));
	}
	return o.join("");
}
function write_ws_xlml(idx, opts, wb) {
	var o = [];
	var s = wb.SheetNames[idx];
	var ws = wb.Sheets[s];

	/* Table */
	var t = ws ? write_ws_xlml_table(ws, opts, idx, wb) : "";
	if(t.length > 0) o.push("<Table>" + t + "</Table>");

	/* WorksheetOptions */
	o.push(write_ws_xlml_wsopts(ws, opts, idx, wb));

	return o.join("");
}
function write_xlml(wb, opts) {
	var d = [];
	d.push(write_props_xlml(wb, opts));
	d.push(write_wb_xlml(wb, opts));
	d.push(write_sty_xlml(wb, opts));
	for(var i = 0; i < wb.SheetNames.length; ++i)
		d.push(writextag("Worksheet", write_ws_xlml(i, opts, wb), {"ss:Name":escapexml(wb.SheetNames[i])}));
	return XML_HEADER + writextag("Workbook", d.join(""), {
		'xmlns':      XLMLNS.ss,
		'xmlns:o':    XLMLNS.o,
		'xmlns:x':    XLMLNS.x,
		'xmlns:ss':   XLMLNS.ss,
		'xmlns:dt':   XLMLNS.dt,
		'xmlns:html': XLMLNS.html
	});
}
/* [MS-OLEDS] 2.3.8 CompObjStream */
function parse_compobj(obj) {
	var v = {};
	var o = obj.content;

	/* [MS-OLEDS] 2.3.7 CompObjHeader -- All fields MUST be ignored */
	var l = 28, m;
	m = __lpstr(o, l);
	l += 4 + __readUInt32LE(o,l);
	v.UserType = m;

	/* [MS-OLEDS] 2.3.1 ClipboardFormatOrAnsiString */
	m = __readUInt32LE(o,l); l+= 4;
	switch(m) {
		case 0x00000000: break;
		case 0xffffffff: case 0xfffffffe: l+=4; break;
		default:
			if(m > 0x190) throw new Error("Unsupported Clipboard: " + m.toString(16));
			l += m;
	}

	m = __lpstr(o, l); l += m.length === 0 ? 0 : 5 + m.length; v.Reserved1 = m;

	if((m = __readUInt32LE(o,l)) !== 0x71b2e9f4) return v;
	throw new Error("Unsupported Unicode Extension");
}

/* 2.4.58 Continue logic */
function slurp(R, blob, length, opts) {
	var l = length;
	var bufs = [];
	var d = blob.slice(blob.l,blob.l+l);
	if(opts && opts.enc && opts.enc.insitu_decrypt) switch(R.n) {
	case 'BOF': case 'FilePass': case 'FileLock': case 'InterfaceHdr': case 'RRDInfo': case 'RRDHead': case 'UsrExcl': break;
	default:
		if(d.length === 0) break;
		opts.enc.insitu_decrypt(d);
	}
	bufs.push(d);
	blob.l += l;
	var next = (XLSRecordEnum[__readUInt16LE(blob,blob.l)]);
	while(next != null && next.n === 'Continue') {
		l = __readUInt16LE(blob,blob.l+2);
		bufs.push(blob.slice(blob.l+4,blob.l+4+l));
		blob.l += 4+l;
		next = (XLSRecordEnum[__readUInt16LE(blob, blob.l)]);
	}
	var b = (bconcat(bufs));
	prep_blob(b, 0);
	var ll = 0; b.lens = [];
	for(var j = 0; j < bufs.length; ++j) { b.lens.push(ll); ll += bufs[j].length; }
	return R.f(b, b.length, opts);
}

function safe_format_xf(p, opts, date1904) {
	if(p.t === 'z') return;
	if(!p.XF) return;
	var fmtid = 0;
	try {
		fmtid = p.z || p.XF.ifmt || 0;
		if(opts.cellNF) p.z = SSF._table[fmtid];
	} catch(e) { if(opts.WTF) throw e; }
	if(!opts || opts.cellText !== false) try {
		if(p.t === 'e') { p.w = p.w || BErr[p.v]; }
		else if(fmtid === 0) {
			if(p.t === 'n') {
				if((p.v|0) === p.v) p.w = SSF._general_int(p.v);
				else p.w = SSF._general_num(p.v);
			}
			else p.w = SSF._general(p.v);
		}
		else p.w = SSF.format(fmtid,p.v, {date1904:!!date1904});
		if(opts.cellDates && fmtid && p.t == 'n' && SSF.is_date(SSF._table[fmtid])) {
			var _d = SSF.parse_date_code(p.v); if(_d) { p.t = 'd'; p.v = new Date(Date.UTC(_d.y, _d.m-1,_d.d,_d.H,_d.M,_d.S,_d.u)); }
		}
	} catch(e) { if(opts.WTF) throw e; }
}

function make_cell(val, ixfe, t) {
	return ({v:val, ixfe:ixfe, t:t});
}

// 2.3.2
function parse_workbook(blob, options) {
	var wb = ({opts:{}});
	var Sheets = {};
	if(DENSE != null && options.dense == null) options.dense = DENSE;
	var out = ((options.dense ? [] : {}));
	var Directory = {};
	var found_sheet = false;
	var range = ({});
	var last_formula = null;
	var sst = [];
	var cur_sheet = "";
	var Preamble = {};
	var lastcell, last_cell = "", cc, cmnt, rng, rngC, rngR;
	var shared_formulae = {};
	var array_formulae = []; /* TODO: something more clever */
	var temp_val;
	var country;
	var cell_valid = true;
	var XFs = []; /* XF records */
	var palette = [];
	var Workbook = ({ Sheets:[] }), wsprops = {};
	var get_rgb = function getrgb(icv) {
		if(icv < 8) return XLSIcv[icv];
		if(icv < 64) return palette[icv-8] || XLSIcv[icv];
		return XLSIcv[icv];
	};
	var process_cell_style = function pcs(cell, line, options) {
		var xfd = line.XF.data;
		if(!xfd || !xfd.patternType || !options || !options.cellStyles) return;
		line.s = ({});
		line.s.patternType = xfd.patternType;
		var t;
		if((t = rgb2Hex(get_rgb(xfd.icvFore)))) { line.s.fgColor = {rgb:t}; }
		if((t = rgb2Hex(get_rgb(xfd.icvBack)))) { line.s.bgColor = {rgb:t}; }
	};
	var addcell = function addcell(cell, line, options) {
		if(file_depth > 1) return;
		if(!cell_valid) return;
		if(options.cellStyles && line.XF && line.XF.data) process_cell_style(cell, line, options);
		lastcell = cell;
		last_cell = encode_cell(cell);
		if(range.s) {
			if(cell.r < range.s.r) range.s.r = cell.r;
			if(cell.c < range.s.c) range.s.c = cell.c;
		}
		if(range.e) {
			if(cell.r + 1 > range.e.r) range.e.r = cell.r + 1;
			if(cell.c + 1 > range.e.c) range.e.c = cell.c + 1;
		}
		if(options.cellFormula && line.f) {
			for(var afi = 0; afi < array_formulae.length; ++afi) {
				if(array_formulae[afi][0].s.c > cell.c) continue;
				if(array_formulae[afi][0].s.r > cell.r) continue;
				if(array_formulae[afi][0].e.c < cell.c) continue;
				if(array_formulae[afi][0].e.r < cell.r) continue;
				line.F = encode_range(array_formulae[afi][0]);
				if(array_formulae[afi][0].s.c != cell.c) delete line.f;
				if(array_formulae[afi][0].s.r != cell.r) delete line.f;
				if(line.f) line.f = "" + stringify_formula(array_formulae[afi][1], range, cell, supbooks, opts);
				break;
			}
		}
		if(options.sheetRows && lastcell.r >= options.sheetRows) cell_valid = false;
		else {
			if(options.dense) {
				if(!out[cell.r]) out[cell.r] = [];
				out[cell.r][cell.c] = line;
			} else out[last_cell] = line;
		}
	};
	var opts = ({
		enc: false, // encrypted
		sbcch: 0, // cch in the preceding SupBook
		snames: [], // sheetnames
		sharedf: shared_formulae, // shared formulae by address
		arrayf: array_formulae, // array formulae array
		rrtabid: [], // RRTabId
		lastuser: "", // Last User from WriteAccess
		biff: 8, // BIFF version
		codepage: 0, // CP from CodePage record
		winlocked: 0, // fLockWn from WinProtect
		cellStyles: !!options && !!options.cellStyles,
		WTF: !!options && !!options.wtf
	});
	if(options.password) opts.password = options.password;
	var mergecells = [];
	var objects = [];
	var colinfo = [], rowinfo = [];
	var defwidth = 0, defheight = 0; // twips / MDW respectively
	var seencol = false;
	var supbooks = ([]); // 1-indexed, will hold extern names
	supbooks.SheetNames = opts.snames;
	supbooks.sharedf = opts.sharedf;
	supbooks.arrayf = opts.arrayf;
	supbooks.names = [];
	supbooks.XTI = [];
	var last_Rn = '';
	var file_depth = 0; /* TODO: make a real stack */
	var BIFF2Fmt = 0;
	var BIFF2FmtTable = [];
	var FilterDatabases = []; /* TODO: sort out supbooks and process elsewhere */
	var last_lbl;

	/* explicit override for some broken writers */
	opts.codepage = 1200;
	set_cp(1200);
	while(blob.l < blob.length - 1) {
		var s = blob.l;
		var RecordType = blob.read_shift(2);
		if(RecordType === 0 && last_Rn === 'EOF') break;
		var length = (blob.l === blob.length ? 0 : blob.read_shift(2)), y;
		var R = XLSRecordEnum[RecordType];
		//console.log(RecordType.toString(16), RecordType, R, blob.l, length, blob.length);
		//if(!R) console.log(blob.slice(blob.l, blob.l + length));
		if(R && R.f) {
			if(options.bookSheets) {
				if(last_Rn === 'BoundSheet8' && R.n !== 'BoundSheet8') break;
			}
			last_Rn = R.n;
			if(R.r === 2 || R.r == 12) {
				var rt = blob.read_shift(2); length -= 2;
				if(!opts.enc && rt !== RecordType) throw "rt mismatch";
				if(R.r == 12){ blob.l += 10; length -= 10; } // skip FRT
			}
			//console.error(R,blob.l,length,blob.length);
			var val;
			if(R.n === 'EOF') val = R.f(blob, length, opts);
			else val = slurp(R, blob, length, opts);
			var Rn = R.n;
			/* nested switch statements to workaround V8 128 limit */
			switch(Rn) {
				/* Workbook Options */
				case 'Date1904': wb.opts.Date1904 = val; break;
				case 'WriteProtect': wb.opts.WriteProtect = true; break;
				case 'FilePass':
					if(!opts.enc) blob.l = 0;
					opts.enc = val;
					if(opts.WTF) console.error(val);
					if(!options.password) throw new Error("File is password-protected");
					if(val.valid == null) throw new Error("Encryption scheme unsupported");
					if(!val.valid) throw new Error("Password is incorrect");
					break;
				case 'WriteAccess': opts.lastuser = val; break;
				case 'FileSharing': break; //TODO
				case 'CodePage':
					/* overrides based on test cases */
					if(val === 0x5212) val = 1200;
					else if(val === 0x8001) val = 1252;
					opts.codepage = val;
					set_cp(val);
					break;
				case 'RRTabId': opts.rrtabid = val; break;
				case 'WinProtect': opts.winlocked = val; break;
				case 'Template': break; // TODO
				case 'RefreshAll': wb.opts.RefreshAll = val; break;
				case 'BookBool': break; // TODO
				case 'UsesELFs': break;
				case 'MTRSettings': break;
				case 'CalcCount': wb.opts.CalcCount = val; break;
				case 'CalcDelta': wb.opts.CalcDelta = val; break;
				case 'CalcIter': wb.opts.CalcIter = val; break;
				case 'CalcMode': wb.opts.CalcMode = val; break;
				case 'CalcPrecision': wb.opts.CalcPrecision = val; break;
				case 'CalcSaveRecalc': wb.opts.CalcSaveRecalc = val; break;
				case 'CalcRefMode': opts.CalcRefMode = val; break; // TODO: implement R1C1
				case 'Uncalced': break;
				case 'ForceFullCalculation': wb.opts.FullCalc = val; break;
				case 'WsBool': break; // TODO
				case 'XF': XFs.push(val); break;
				case 'ExtSST': break; // TODO
				case 'BookExt': break; // TODO
				case 'RichTextStream': break;
				case 'BkHim': break;

				case 'SupBook':
					supbooks.push([val]);
					supbooks[supbooks.length-1].XTI = [];
					break;
				case 'ExternName':
					supbooks[supbooks.length-1].push(val);
					break;
				case 'Index': break; // TODO
				case 'Lbl':
					last_lbl = ({
						Name: val.Name,
						Ref: stringify_formula(val.rgce,range,null,supbooks,opts)
					});
					if(val.itab > 0) last_lbl.Sheet = val.itab - 1;
					supbooks.names.push(last_lbl);
					if(!supbooks[0]) supbooks[0] = [];
					supbooks[supbooks.length-1].push(val);
					if(val.Name == "\r" && val.itab > 0)
						if(val.rgce && val.rgce[0] && val.rgce[0][0] && val.rgce[0][0][0] == 'PtgArea3d')
							FilterDatabases[val.itab - 1] = { ref: encode_range(val.rgce[0][0][1][2]) };
					break;
				case 'ExternSheet':
					if(supbooks.length == 0) { supbooks[0] = []; supbooks[0].XTI = []; }
					supbooks[supbooks.length - 1].XTI = supbooks[supbooks.length - 1].XTI.concat(val); supbooks.XTI = supbooks.XTI.concat(val); break;
				case 'NameCmt':
					/* TODO: search for correct name */
					if(opts.biff < 8) break;
					if(last_lbl != null) last_lbl.Comment = val[1];
					break;

				case 'Protect': out["!protect"] = val; break; /* for sheet or book */
				case 'Password': if(val !== 0 && opts.WTF) console.error("Password verifier: " + val); break;
				case 'Prot4Rev': case 'Prot4RevPass': break; /*TODO: Revision Control*/

				case 'BoundSheet8': {
					Directory[val.pos] = val;
					opts.snames.push(val.name);
				} break;
				case 'EOF': {
					if(--file_depth) break;
					if(range.e) {
						if(range.e.r > 0 && range.e.c > 0) {
							range.e.r--; range.e.c--;
							out["!ref"] = encode_range(range);
							range.e.r++; range.e.c++;
						}
						if(mergecells.length > 0) out["!merges"] = mergecells;
						if(objects.length > 0) out["!objects"] = objects;
						if(colinfo.length > 0) out["!cols"] = colinfo;
						if(rowinfo.length > 0) out["!rows"] = rowinfo;
						Workbook.Sheets.push(wsprops);
					}
					if(cur_sheet === "") Preamble = out; else Sheets[cur_sheet] = out;
					out = ((options.dense ? [] : {}));
				} break;
				case 'BOF': {
					if(opts.biff !== 8){/* empty */}
					else if(RecordType  === 0x0009) opts.biff = 2;
					else if(RecordType  === 0x0209) opts.biff = 3;
					else if(RecordType  === 0x0409) opts.biff = 4;
					else if(val.BIFFVer === 0x0500) opts.biff = 5;
					else if(val.BIFFVer === 0x0600) opts.biff = 8;
					else if(val.BIFFVer === 0x0002) opts.biff = 2;
					else if(val.BIFFVer === 0x0007) opts.biff = 2;
					if(file_depth++) break;
					cell_valid = true;
					out = ((options.dense ? [] : {}));

					if(opts.biff < 5) {
						if(cur_sheet === "") cur_sheet = "Sheet1";
						range = {s:{r:0,c:0},e:{r:0,c:0}};
						/* fake BoundSheet8 */
						var fakebs8 = {pos: blob.l - length, name:cur_sheet};
						Directory[fakebs8.pos] = fakebs8;
						opts.snames.push(cur_sheet);
					}
					else cur_sheet = (Directory[s] || {name:""}).name;
					if(val.dt == 0x20) out["!type"] = "chart";
					mergecells = [];
					objects = [];
					array_formulae = []; opts.arrayf = array_formulae;
					colinfo = []; rowinfo = [];
					defwidth = defheight = 0;
					seencol = false;
					wsprops = {Hidden:(Directory[s]||{hs:0}).hs, name:cur_sheet };
				} break;

				case 'Number': case 'BIFF2NUM': case 'BIFF2INT': {
					if(out["!type"] == "chart") if(options.dense ? (out[val.r]||[])[val.c]: out[encode_cell({c:val.c, r:val.r})]) ++val.c;
					temp_val = ({ixfe: val.ixfe, XF: XFs[val.ixfe]||{}, v:val.val, t:'n'});
					if(BIFF2Fmt > 0) temp_val.z = BIFF2FmtTable[(temp_val.ixfe>>8) & 0x1F];
					safe_format_xf(temp_val, options, wb.opts.Date1904);
					addcell({c:val.c, r:val.r}, temp_val, options);
				} break;
				case 'BoolErr': {
					temp_val = ({ixfe: val.ixfe, XF: XFs[val.ixfe], v:val.val, t:val.t});
					if(BIFF2Fmt > 0) temp_val.z = BIFF2FmtTable[(temp_val.ixfe>>8) & 0x1F];
					safe_format_xf(temp_val, options, wb.opts.Date1904);
					addcell({c:val.c, r:val.r}, temp_val, options);
				} break;
				case 'RK': {
					temp_val = ({ixfe: val.ixfe, XF: XFs[val.ixfe], v:val.rknum, t:'n'});
					if(BIFF2Fmt > 0) temp_val.z = BIFF2FmtTable[(temp_val.ixfe>>8) & 0x1F];
					safe_format_xf(temp_val, options, wb.opts.Date1904);
					addcell({c:val.c, r:val.r}, temp_val, options);
				} break;
				case 'MulRk': {
					for(var j = val.c; j <= val.C; ++j) {
						var ixfe = val.rkrec[j-val.c][0];
						temp_val= ({ixfe:ixfe, XF:XFs[ixfe], v:val.rkrec[j-val.c][1], t:'n'});
						if(BIFF2Fmt > 0) temp_val.z = BIFF2FmtTable[(temp_val.ixfe>>8) & 0x1F];
						safe_format_xf(temp_val, options, wb.opts.Date1904);
						addcell({c:j, r:val.r}, temp_val, options);
					}
				} break;
				case 'Formula': {
					if(val.val == 'String') { last_formula = val; break; }
					temp_val = make_cell(val.val, val.cell.ixfe, val.tt);
					temp_val.XF = XFs[temp_val.ixfe];
					if(options.cellFormula) {
						var _f = val.formula;
						if(_f && _f[0] && _f[0][0] && _f[0][0][0] == 'PtgExp') {
							var _fr = _f[0][0][1][0], _fc = _f[0][0][1][1];
							var _fe = encode_cell({r:_fr, c:_fc});
							if(shared_formulae[_fe]) temp_val.f = ""+stringify_formula(val.formula,range,val.cell,supbooks, opts);
							else temp_val.F = ((options.dense ? (out[_fr]||[])[_fc]: out[_fe]) || {}).F;
						} else temp_val.f = ""+stringify_formula(val.formula,range,val.cell,supbooks, opts);
					}
					if(BIFF2Fmt > 0) temp_val.z = BIFF2FmtTable[(temp_val.ixfe>>8) & 0x1F];
					safe_format_xf(temp_val, options, wb.opts.Date1904);
					addcell(val.cell, temp_val, options);
					last_formula = val;
				} break;
				case 'String': {
					if(last_formula) { /* technically always true */
						last_formula.val = val;
						temp_val = make_cell(val, last_formula.cell.ixfe, 's');
						temp_val.XF = XFs[temp_val.ixfe];
						if(options.cellFormula) {
							temp_val.f = ""+stringify_formula(last_formula.formula, range, last_formula.cell, supbooks, opts);
						}
						if(BIFF2Fmt > 0) temp_val.z = BIFF2FmtTable[(temp_val.ixfe>>8) & 0x1F];
						safe_format_xf(temp_val, options, wb.opts.Date1904);
						addcell(last_formula.cell, temp_val, options);
						last_formula = null;
					} else throw new Error("String record expects Formula");
				} break;
				case 'Array': {
					array_formulae.push(val);
					var _arraystart = encode_cell(val[0].s);
					cc = options.dense ? (out[val[0].s.r]||[])[val[0].s.c] : out[_arraystart];
					if(options.cellFormula && cc) {
						if(!last_formula) break; /* technically unreachable */
						if(!_arraystart || !cc) break;
						cc.f = ""+stringify_formula(val[1], range, val[0], supbooks, opts);
						cc.F = encode_range(val[0]);
					}
				} break;
				case 'ShrFmla': {
					if(!cell_valid) break;
					if(!options.cellFormula) break;
					if(last_cell) {
						/* TODO: capture range */
						if(!last_formula) break; /* technically unreachable */
						shared_formulae[encode_cell(last_formula.cell)]= val[0];
						cc = options.dense ? (out[last_formula.cell.r]||[])[last_formula.cell.c] : out[encode_cell(last_formula.cell)];
						(cc||{}).f = ""+stringify_formula(val[0], range, lastcell, supbooks, opts);
					}
				} break;
				case 'LabelSst':
					temp_val=make_cell(sst[val.isst].t, val.ixfe, 's');
					temp_val.XF = XFs[temp_val.ixfe];
					if(BIFF2Fmt > 0) temp_val.z = BIFF2FmtTable[(temp_val.ixfe>>8) & 0x1F];
					safe_format_xf(temp_val, options, wb.opts.Date1904);
					addcell({c:val.c, r:val.r}, temp_val, options);
					break;
				case 'Blank': if(options.sheetStubs) {
					temp_val = ({ixfe: val.ixfe, XF: XFs[val.ixfe], t:'z'});
					if(BIFF2Fmt > 0) temp_val.z = BIFF2FmtTable[(temp_val.ixfe>>8) & 0x1F];
					safe_format_xf(temp_val, options, wb.opts.Date1904);
					addcell({c:val.c, r:val.r}, temp_val, options);
				} break;
				case 'MulBlank': if(options.sheetStubs) {
					for(var _j = val.c; _j <= val.C; ++_j) {
						var _ixfe = val.ixfe[_j-val.c];
						temp_val= ({ixfe:_ixfe, XF:XFs[_ixfe], t:'z'});
						if(BIFF2Fmt > 0) temp_val.z = BIFF2FmtTable[(temp_val.ixfe>>8) & 0x1F];
						safe_format_xf(temp_val, options, wb.opts.Date1904);
						addcell({c:_j, r:val.r}, temp_val, options);
					}
				} break;
				case 'RString':
				case 'Label': case 'BIFF2STR':
					temp_val=make_cell(val.val, val.ixfe, 's');
					temp_val.XF = XFs[temp_val.ixfe];
					if(BIFF2Fmt > 0) temp_val.z = BIFF2FmtTable[(temp_val.ixfe>>8) & 0x1F];
					safe_format_xf(temp_val, options, wb.opts.Date1904);
					addcell({c:val.c, r:val.r}, temp_val, options);
					break;

				case 'Dimensions': {
					if(file_depth === 1) range = val; /* TODO: stack */
				} break;
				case 'SST': {
					sst = val;
				} break;
				case 'Format': { /* val = [id, fmt] */
					SSF.load(val[1], val[0]);
				} break;
				case 'BIFF2FORMAT': {
					BIFF2FmtTable[BIFF2Fmt++] = val;
					for(var b2idx = 0; b2idx < BIFF2Fmt + 163; ++b2idx) if(SSF._table[b2idx] == val) break;
					if(b2idx >= 163) SSF.load(val, BIFF2Fmt + 163);
				} break;

				case 'MergeCells': mergecells = mergecells.concat(val); break;

				case 'Obj': objects[val.cmo[0]] = opts.lastobj = val; break;
				case 'TxO': opts.lastobj.TxO = val; break;
				case 'ImData': opts.lastobj.ImData = val; break;

				case 'HLink': {
					for(rngR = val[0].s.r; rngR <= val[0].e.r; ++rngR)
						for(rngC = val[0].s.c; rngC <= val[0].e.c; ++rngC) {
							cc = options.dense ? (out[rngR]||[])[rngC] : out[encode_cell({c:rngC,r:rngR})];
							if(cc) cc.l = val[1];
						}
				} break;
				case 'HLinkTooltip': {
					for(rngR = val[0].s.r; rngR <= val[0].e.r; ++rngR)
						for(rngC = val[0].s.c; rngC <= val[0].e.c; ++rngC) {
							cc = options.dense ? (out[rngR]||[])[rngC] : out[encode_cell({c:rngC,r:rngR})];
							if(cc) cc.l.Tooltip = val[1];
							}
				} break;

				/* Comments */
				case 'Note': {
					if(opts.biff <= 5 && opts.biff >= 2) break; /* TODO: BIFF5 */
					cc = options.dense ? (out[val[0].r]||[])[val[0].c] : out[encode_cell(val[0])];
					var noteobj = objects[val[2]];
					if(!cc) break;
					if(!cc.c) cc.c = [];
					cmnt = {a:val[1],t:noteobj.TxO.t};
					cc.c.push(cmnt);
				} break;

				default: switch(R.n) { /* nested */
				case 'ClrtClient': break;
				case 'XFExt': update_xfext(XFs[val.ixfe], val.ext); break;

				case 'DefColWidth': defwidth = val; break;
				case 'DefaultRowHeight': defheight = val[1]; break; // TODO: flags

				case 'ColInfo': {
					if(!opts.cellStyles) break;
					while(val.e >= val.s) {
						colinfo[val.e--] = { width: val.w/256 };
						if(!seencol) { seencol = true; find_mdw_colw(val.w/256); }
						process_col(colinfo[val.e+1]);
					}
				} break;
				case 'Row': {
					var rowobj = {};
					if(val.hidden) { rowinfo[val.r] = rowobj; rowobj.hidden = true; }
					if(val.hpt) {
						rowinfo[val.r] = rowobj;
						rowobj.hpt = val.hpt; rowobj.hpx = pt2px(val.hpt);
					}
				} break;

				case 'LeftMargin':
				case 'RightMargin':
				case 'TopMargin':
				case 'BottomMargin':
					if(!out['!margins']) default_margins(out['!margins'] = {});
					out['!margins'][Rn.slice(0,-6).toLowerCase()] = val;
					break;

				case 'Setup': // TODO
					if(!out['!margins']) default_margins(out['!margins'] = {});
					out['!margins'].header = val.header;
					out['!margins'].footer = val.footer;
					break;

				case 'Header': break; // TODO
				case 'Footer': break; // TODO
				case 'HCenter': break; // TODO
				case 'VCenter': break; // TODO
				case 'Pls': break; // TODO
				case 'GCW': break;
				case 'LHRecord': break;
				case 'DBCell': break; // TODO
				case 'EntExU2': break; // TODO
				case 'SxView': break; // TODO
				case 'Sxvd': break; // TODO
				case 'SXVI': break; // TODO
				case 'SXVDEx': break; // TODO
				case 'SxIvd': break; // TODO
				case 'SXDI': break; // TODO
				case 'SXLI': break; // TODO
				case 'SXEx': break; // TODO
				case 'QsiSXTag': break; // TODO
				case 'Selection': break;
				case 'Feat': break;
				case 'FeatHdr': case 'FeatHdr11': break;
				case 'Feature11': case 'Feature12': case 'List12': break;
				case 'Country': country = val; break;
				case 'RecalcId': break;
				case 'DxGCol': break; // TODO: htmlify
				case 'Fbi': case 'Fbi2': case 'GelFrame': break;
				case 'Font': break; // TODO
				case 'XFCRC': break; // TODO
				case 'Style': break; // TODO
				case 'StyleExt': break; // TODO
				case 'Palette': palette = val; break; // TODO
				case 'Theme': break; // TODO
				/* Protection */
				case 'ScenarioProtect': break;
				case 'ObjProtect': break;

				/* Conditional Formatting */
				case 'CondFmt12': break;

				/* Table */
				case 'Table': break; // TODO
				case 'TableStyles': break; // TODO
				case 'TableStyle': break; // TODO
				case 'TableStyleElement': break; // TODO

				/* PivotTable */
				case 'SXStreamID': break; // TODO
				case 'SXVS': break; // TODO
				case 'DConRef': break; // TODO
				case 'SXAddl': break; // TODO
				case 'DConBin': break; // TODO
				case 'DConName': break; // TODO
				case 'SXPI': break; // TODO
				case 'SxFormat': break; // TODO
				case 'SxSelect': break; // TODO
				case 'SxRule': break; // TODO
				case 'SxFilt': break; // TODO
				case 'SxItm': break; // TODO
				case 'SxDXF': break; // TODO

				/* Scenario Manager */
				case 'ScenMan': break;

				/* Data Consolidation */
				case 'DCon': break;

				/* Watched Cell */
				case 'CellWatch': break;

				/* Print Settings */
				case 'PrintRowCol': break;
				case 'PrintGrid': break;
				case 'PrintSize': break;

				case 'XCT': break;
				case 'CRN': break;

				case 'Scl': {
					//console.log("Zoom Level:", val[0]/val[1],val);
				} break;
				case 'SheetExt': {
					/* empty */
				} break;
				case 'SheetExtOptional': {
					/* empty */
				} break;

				/* VBA */
				case 'ObNoMacros': {
					/* empty */
				} break;
				case 'ObProj': {
					/* empty */
				} break;
				case 'CodeName': {
					/* empty */
				} break;
				case 'GUIDTypeLib': {
					/* empty */
				} break;

				case 'WOpt': break; // TODO: WTF?
				case 'PhoneticInfo': break;

				case 'OleObjectSize': break;

				/* Differential Formatting */
				case 'DXF': case 'DXFN': case 'DXFN12': case 'DXFN12List': case 'DXFN12NoCB': break;

				/* Data Validation */
				case 'Dv': case 'DVal': break;

				/* Data Series */
				case 'BRAI': case 'Series': case 'SeriesText': break;

				/* Data Connection */
				case 'DConn': break;
				case 'DbOrParamQry': break;
				case 'DBQueryExt': break;

				/* Formatting */
				case 'IFmtRecord': break;
				case 'CondFmt': case 'CF': case 'CF12': case 'CFEx': break;

				/* Explicitly Ignored */
				case 'Excel9File': break;
				case 'Units': break;
				case 'InterfaceHdr': case 'Mms': case 'InterfaceEnd': case 'DSF': case 'BuiltInFnGroupCount': break;
				/* View Stuff */
				case 'Window1': case 'Window2': case 'HideObj': case 'GridSet': case 'Guts':
				case 'UserBView': case 'UserSViewBegin': case 'UserSViewEnd':
				case 'Pane': break;
				default: switch(R.n) { /* nested */
				/* Chart */
				case 'Dat':
				case 'Begin': case 'End':
				case 'StartBlock': case 'EndBlock':
				case 'Frame': case 'Area':
				case 'Axis': case 'AxisLine': case 'Tick': break;
				case 'AxesUsed':
				case 'CrtLayout12': case 'CrtLayout12A': case 'CrtLink': case 'CrtLine': case 'CrtMlFrt': case 'CrtMlFrtContinue': break;
				case 'LineFormat': case 'AreaFormat':
				case 'Chart': case 'Chart3d': case 'Chart3DBarShape': case 'ChartFormat': case 'ChartFrtInfo': break;
				case 'PlotArea': case 'PlotGrowth': break;
				case 'SeriesList': case 'SerParent': case 'SerAuxTrend': break;
				case 'DataFormat': case 'SerToCrt': case 'FontX': break;
				case 'CatSerRange': case 'AxcExt': case 'SerFmt': break;
				case 'ShtProps': break;
				case 'DefaultText': case 'Text': case 'CatLab': break;
				case 'DataLabExtContents': break;
				case 'Legend': case 'LegendException': break;
				case 'Pie': case 'Scatter': break;
				case 'PieFormat': case 'MarkerFormat': break;
				case 'StartObject': case 'EndObject': break;
				case 'AlRuns': case 'ObjectLink': break;
				case 'SIIndex': break;
				case 'AttachedLabel': case 'YMult': break;

				/* Chart Group */
				case 'Line': case 'Bar': break;
				case 'Surf': break;

				/* Axis Group */
				case 'AxisParent': break;
				case 'Pos': break;
				case 'ValueRange': break;

				/* Pivot Chart */
				case 'SXViewEx9': break; // TODO
				case 'SXViewLink': break;
				case 'PivotChartBits': break;
				case 'SBaseRef': break;
				case 'TextPropsStream': break;

				/* Chart Misc */
				case 'LnExt': break;
				case 'MkrExt': break;
				case 'CrtCoopt': break;

				/* Query Table */
				case 'Qsi': case 'Qsif': case 'Qsir': case 'QsiSXTag': break;
				case 'TxtQry': break;

				/* Filter */
				case 'FilterMode': break;
				case 'AutoFilter': case 'AutoFilterInfo': break;
				case 'AutoFilter12': break;
				case 'DropDownObjIds': break;
				case 'Sort': break;
				case 'SortData': break;

				/* Drawing */
				case 'ShapePropsStream': break;
				case 'MsoDrawing': case 'MsoDrawingGroup': case 'MsoDrawingSelection': break;
				/* Pub Stuff */
				case 'WebPub': case 'AutoWebPub': break;

				/* Print Stuff */
				case 'HeaderFooter': case 'HFPicture': case 'PLV':
				case 'HorizontalPageBreaks': case 'VerticalPageBreaks': break;
				/* Behavioral */
				case 'Backup': case 'CompressPictures': case 'Compat12': break;

				/* Should not Happen */
				case 'Continue': case 'ContinueFrt12': break;

				/* Future Records */
				case 'FrtFontList': case 'FrtWrapper': break;

				default: switch(R.n) { /* nested */
				/* BIFF5 records */
				case 'ExternCount': break;
				case 'TabIdConf': case 'Radar': case 'RadarArea': case 'DropBar': case 'Intl': case 'CoordList': case 'SerAuxErrBar': break;

				/* BIFF2-4 records */
				case 'BIFF2FONTCLR': case 'BIFF2FMTCNT': case 'BIFF2FONTXTRA': break;
				case 'BIFF2XF': case 'BIFF3XF': case 'BIFF4XF': break;
				case 'BIFF4FMTCNT': case 'BIFF2ROW': case 'BIFF2WINDOW2': break;

				/* Miscellaneous */
				case 'SCENARIO': case 'DConBin': case 'PicF': case 'DataLabExt':
				case 'Lel': case 'BopPop': case 'BopPopCustom': case 'RealTimeData':
				case 'Name': break;
				default: if(options.WTF) throw 'Unrecognized Record ' + R.n;
			}}}}
		} else blob.l += length;
	}
	var sheetnamesraw = Object.keys(Directory).sort(function(a,b) { return Number(a) - Number(b); }).map(function(x){return Directory[x].name;});
	var sheetnames = sheetnamesraw.slice();
	wb.Directory=sheetnamesraw;
	wb.SheetNames=sheetnamesraw;
	if(!options.bookSheets) wb.Sheets=Sheets;
	if(wb.Sheets) FilterDatabases.forEach(function(r,i) { wb.Sheets[wb.SheetNames[i]]['!autofilter'] = r; });
	wb.Preamble=Preamble;
	wb.Strings = sst;
	wb.SSF = SSF.get_table();
	if(opts.enc) wb.Encryption = opts.enc;
	wb.Metadata = {};
	if(country !== undefined) wb.Metadata.Country = country;
	if(supbooks.names.length > 0) Workbook.Names = supbooks.names;
	wb.Workbook = Workbook;
	return wb;
}

/* TODO: WTF */
function parse_props(cfb) {
	/* [MS-OSHARED] 2.3.3.2.2 Document Summary Information Property Set */
	var DSI = cfb.find('!DocumentSummaryInformation');
	if(DSI) try { cfb.DocSummary = parse_PropertySetStream(DSI, DocSummaryPIDDSI); } catch(e) {/* empty */}

	/* [MS-OSHARED] 2.3.3.2.1 Summary Information Property Set*/
	var SI = cfb.find('!SummaryInformation');
	if(SI) try { cfb.Summary = parse_PropertySetStream(SI, SummaryPIDSI); } catch(e) {/* empty */}
}

function parse_xlscfb(cfb, options) {
if(!options) options = {};
fix_read_opts(options);
reset_cp();
var CompObj, Summary, Workbook;
if(cfb.FullPaths) {
	CompObj = cfb.find('!CompObj');
	Summary = cfb.find('!SummaryInformation');
	Workbook = cfb.find('/Workbook');
} else {
	prep_blob(cfb, 0);
	Workbook = ({content: cfb});
}

if(!Workbook) Workbook = cfb.find('/Book');
var CompObjP, SummaryP, WorkbookP;

if(CompObj) CompObjP = parse_compobj(CompObj);
if(options.bookProps && !options.bookSheets) WorkbookP = ({});
else {
	if(Workbook) WorkbookP = parse_workbook(Workbook.content, options, !!Workbook.find);
	/* Quattro Pro 7-8 */
	else if(cfb.find('PerfectOffice_MAIN')) WorkbookP = WK_.to_workbook(cfb.find('PerfectOffice_MAIN').content, options);
	/* Quattro Pro 9 */
	else if(cfb.find('NativeContent_MAIN')) WorkbookP = WK_.to_workbook(cfb.find('NativeContent_MAIN').content, options);
	else throw new Error("Cannot find Workbook stream");
}

if(cfb.FullPaths) parse_props(cfb);

var props = {};
for(var y in cfb.Summary) props[y] = cfb.Summary[y];
for(y in cfb.DocSummary) props[y] = cfb.DocSummary[y];
WorkbookP.Props = WorkbookP.Custprops = props; /* TODO: split up properties */
if(options.bookFiles) WorkbookP.cfb = cfb;
/*WorkbookP.CompObjP = CompObjP; // TODO: storage? */
return WorkbookP;
}

/* [MS-XLSB] 2.3 Record Enumeration */
var XLSBRecordEnum = {
0x0000: { n:"BrtRowHdr", f:parse_BrtRowHdr },
0x0001: { n:"BrtCellBlank", f:parse_BrtCellBlank },
0x0002: { n:"BrtCellRk", f:parse_BrtCellRk },
0x0003: { n:"BrtCellError", f:parse_BrtCellError },
0x0004: { n:"BrtCellBool", f:parse_BrtCellBool },
0x0005: { n:"BrtCellReal", f:parse_BrtCellReal },
0x0006: { n:"BrtCellSt", f:parse_BrtCellSt },
0x0007: { n:"BrtCellIsst", f:parse_BrtCellIsst },
0x0008: { n:"BrtFmlaString", f:parse_BrtFmlaString },
0x0009: { n:"BrtFmlaNum", f:parse_BrtFmlaNum },
0x000A: { n:"BrtFmlaBool", f:parse_BrtFmlaBool },
0x000B: { n:"BrtFmlaError", f:parse_BrtFmlaError },
0x0010: { n:"BrtFRTArchID$", f:parse_BrtFRTArchID$ },
0x0013: { n:"BrtSSTItem", f:parse_RichStr },
0x0014: { n:"BrtPCDIMissing", f:parsenoop },
0x0015: { n:"BrtPCDINumber", f:parsenoop },
0x0016: { n:"BrtPCDIBoolean", f:parsenoop },
0x0017: { n:"BrtPCDIError", f:parsenoop },
0x0018: { n:"BrtPCDIString", f:parsenoop },
0x0019: { n:"BrtPCDIDatetime", f:parsenoop },
0x001A: { n:"BrtPCDIIndex", f:parsenoop },
0x001B: { n:"BrtPCDIAMissing", f:parsenoop },
0x001C: { n:"BrtPCDIANumber", f:parsenoop },
0x001D: { n:"BrtPCDIABoolean", f:parsenoop },
0x001E: { n:"BrtPCDIAError", f:parsenoop },
0x001F: { n:"BrtPCDIAString", f:parsenoop },
0x0020: { n:"BrtPCDIADatetime", f:parsenoop },
0x0021: { n:"BrtPCRRecord", f:parsenoop },
0x0022: { n:"BrtPCRRecordDt", f:parsenoop },
0x0023: { n:"BrtFRTBegin", f:parsenoop },
0x0024: { n:"BrtFRTEnd", f:parsenoop },
0x0025: { n:"BrtACBegin", f:parsenoop },
0x0026: { n:"BrtACEnd", f:parsenoop },
0x0027: { n:"BrtName", f:parse_BrtName },
0x0028: { n:"BrtIndexRowBlock", f:parsenoop },
0x002A: { n:"BrtIndexBlock", f:parsenoop },
0x002B: { n:"BrtFont", f:parse_BrtFont },
0x002C: { n:"BrtFmt", f:parse_BrtFmt },
0x002D: { n:"BrtFill", f:parsenoop },
0x002E: { n:"BrtBorder", f:parsenoop },
0x002F: { n:"BrtXF", f:parse_BrtXF },
0x0030: { n:"BrtStyle", f:parsenoop },
0x0031: { n:"BrtCellMeta", f:parsenoop },
0x0032: { n:"BrtValueMeta", f:parsenoop },
0x0033: { n:"BrtMdb", f:parsenoop },
0x0034: { n:"BrtBeginFmd", f:parsenoop },
0x0035: { n:"BrtEndFmd", f:parsenoop },
0x0036: { n:"BrtBeginMdx", f:parsenoop },
0x0037: { n:"BrtEndMdx", f:parsenoop },
0x0038: { n:"BrtBeginMdxTuple", f:parsenoop },
0x0039: { n:"BrtEndMdxTuple", f:parsenoop },
0x003A: { n:"BrtMdxMbrIstr", f:parsenoop },
0x003B: { n:"BrtStr", f:parsenoop },
0x003C: { n:"BrtColInfo", f:parse_ColInfo },
0x003E: { n:"BrtCellRString", f:parsenoop },
0x003F: { n:"BrtCalcChainItem$", f:parse_BrtCalcChainItem$ },
0x0040: { n:"BrtDVal", f:parsenoop },
0x0041: { n:"BrtSxvcellNum", f:parsenoop },
0x0042: { n:"BrtSxvcellStr", f:parsenoop },
0x0043: { n:"BrtSxvcellBool", f:parsenoop },
0x0044: { n:"BrtSxvcellErr", f:parsenoop },
0x0045: { n:"BrtSxvcellDate", f:parsenoop },
0x0046: { n:"BrtSxvcellNil", f:parsenoop },
0x0080: { n:"BrtFileVersion", f:parsenoop },
0x0081: { n:"BrtBeginSheet", f:parsenoop },
0x0082: { n:"BrtEndSheet", f:parsenoop },
0x0083: { n:"BrtBeginBook", f:parsenoop, p:0 },
0x0084: { n:"BrtEndBook", f:parsenoop },
0x0085: { n:"BrtBeginWsViews", f:parsenoop },
0x0086: { n:"BrtEndWsViews", f:parsenoop },
0x0087: { n:"BrtBeginBookViews", f:parsenoop },
0x0088: { n:"BrtEndBookViews", f:parsenoop },
0x0089: { n:"BrtBeginWsView", f:parsenoop },
0x008A: { n:"BrtEndWsView", f:parsenoop },
0x008B: { n:"BrtBeginCsViews", f:parsenoop },
0x008C: { n:"BrtEndCsViews", f:parsenoop },
0x008D: { n:"BrtBeginCsView", f:parsenoop },
0x008E: { n:"BrtEndCsView", f:parsenoop },
0x008F: { n:"BrtBeginBundleShs", f:parsenoop },
0x0090: { n:"BrtEndBundleShs", f:parsenoop },
0x0091: { n:"BrtBeginSheetData", f:parsenoop },
0x0092: { n:"BrtEndSheetData", f:parsenoop },
0x0093: { n:"BrtWsProp", f:parse_BrtWsProp },
0x0094: { n:"BrtWsDim", f:parse_BrtWsDim, p:16 },
0x0097: { n:"BrtPane", f:parsenoop },
0x0098: { n:"BrtSel", f:parsenoop },
0x0099: { n:"BrtWbProp", f:parse_BrtWbProp },
0x009A: { n:"BrtWbFactoid", f:parsenoop },
0x009B: { n:"BrtFileRecover", f:parsenoop },
0x009C: { n:"BrtBundleSh", f:parse_BrtBundleSh },
0x009D: { n:"BrtCalcProp", f:parsenoop },
0x009E: { n:"BrtBookView", f:parsenoop },
0x009F: { n:"BrtBeginSst", f:parse_BrtBeginSst },
0x00A0: { n:"BrtEndSst", f:parsenoop },
0x00A1: { n:"BrtBeginAFilter", f:parse_UncheckedRfX },
0x00A2: { n:"BrtEndAFilter", f:parsenoop },
0x00A3: { n:"BrtBeginFilterColumn", f:parsenoop },
0x00A4: { n:"BrtEndFilterColumn", f:parsenoop },
0x00A5: { n:"BrtBeginFilters", f:parsenoop },
0x00A6: { n:"BrtEndFilters", f:parsenoop },
0x00A7: { n:"BrtFilter", f:parsenoop },
0x00A8: { n:"BrtColorFilter", f:parsenoop },
0x00A9: { n:"BrtIconFilter", f:parsenoop },
0x00AA: { n:"BrtTop10Filter", f:parsenoop },
0x00AB: { n:"BrtDynamicFilter", f:parsenoop },
0x00AC: { n:"BrtBeginCustomFilters", f:parsenoop },
0x00AD: { n:"BrtEndCustomFilters", f:parsenoop },
0x00AE: { n:"BrtCustomFilter", f:parsenoop },
0x00AF: { n:"BrtAFilterDateGroupItem", f:parsenoop },
0x00B0: { n:"BrtMergeCell", f:parse_BrtMergeCell },
0x00B1: { n:"BrtBeginMergeCells", f:parsenoop },
0x00B2: { n:"BrtEndMergeCells", f:parsenoop },
0x00B3: { n:"BrtBeginPivotCacheDef", f:parsenoop },
0x00B4: { n:"BrtEndPivotCacheDef", f:parsenoop },
0x00B5: { n:"BrtBeginPCDFields", f:parsenoop },
0x00B6: { n:"BrtEndPCDFields", f:parsenoop },
0x00B7: { n:"BrtBeginPCDField", f:parsenoop },
0x00B8: { n:"BrtEndPCDField", f:parsenoop },
0x00B9: { n:"BrtBeginPCDSource", f:parsenoop },
0x00BA: { n:"BrtEndPCDSource", f:parsenoop },
0x00BB: { n:"BrtBeginPCDSRange", f:parsenoop },
0x00BC: { n:"BrtEndPCDSRange", f:parsenoop },
0x00BD: { n:"BrtBeginPCDFAtbl", f:parsenoop },
0x00BE: { n:"BrtEndPCDFAtbl", f:parsenoop },
0x00BF: { n:"BrtBeginPCDIRun", f:parsenoop },
0x00C0: { n:"BrtEndPCDIRun", f:parsenoop },
0x00C1: { n:"BrtBeginPivotCacheRecords", f:parsenoop },
0x00C2: { n:"BrtEndPivotCacheRecords", f:parsenoop },
0x00C3: { n:"BrtBeginPCDHierarchies", f:parsenoop },
0x00C4: { n:"BrtEndPCDHierarchies", f:parsenoop },
0x00C5: { n:"BrtBeginPCDHierarchy", f:parsenoop },
0x00C6: { n:"BrtEndPCDHierarchy", f:parsenoop },
0x00C7: { n:"BrtBeginPCDHFieldsUsage", f:parsenoop },
0x00C8: { n:"BrtEndPCDHFieldsUsage", f:parsenoop },
0x00C9: { n:"BrtBeginExtConnection", f:parsenoop },
0x00CA: { n:"BrtEndExtConnection", f:parsenoop },
0x00CB: { n:"BrtBeginECDbProps", f:parsenoop },
0x00CC: { n:"BrtEndECDbProps", f:parsenoop },
0x00CD: { n:"BrtBeginECOlapProps", f:parsenoop },
0x00CE: { n:"BrtEndECOlapProps", f:parsenoop },
0x00CF: { n:"BrtBeginPCDSConsol", f:parsenoop },
0x00D0: { n:"BrtEndPCDSConsol", f:parsenoop },
0x00D1: { n:"BrtBeginPCDSCPages", f:parsenoop },
0x00D2: { n:"BrtEndPCDSCPages", f:parsenoop },
0x00D3: { n:"BrtBeginPCDSCPage", f:parsenoop },
0x00D4: { n:"BrtEndPCDSCPage", f:parsenoop },
0x00D5: { n:"BrtBeginPCDSCPItem", f:parsenoop },
0x00D6: { n:"BrtEndPCDSCPItem", f:parsenoop },
0x00D7: { n:"BrtBeginPCDSCSets", f:parsenoop },
0x00D8: { n:"BrtEndPCDSCSets", f:parsenoop },
0x00D9: { n:"BrtBeginPCDSCSet", f:parsenoop },
0x00DA: { n:"BrtEndPCDSCSet", f:parsenoop },
0x00DB: { n:"BrtBeginPCDFGroup", f:parsenoop },
0x00DC: { n:"BrtEndPCDFGroup", f:parsenoop },
0x00DD: { n:"BrtBeginPCDFGItems", f:parsenoop },
0x00DE: { n:"BrtEndPCDFGItems", f:parsenoop },
0x00DF: { n:"BrtBeginPCDFGRange", f:parsenoop },
0x00E0: { n:"BrtEndPCDFGRange", f:parsenoop },
0x00E1: { n:"BrtBeginPCDFGDiscrete", f:parsenoop },
0x00E2: { n:"BrtEndPCDFGDiscrete", f:parsenoop },
0x00E3: { n:"BrtBeginPCDSDTupleCache", f:parsenoop },
0x00E4: { n:"BrtEndPCDSDTupleCache", f:parsenoop },
0x00E5: { n:"BrtBeginPCDSDTCEntries", f:parsenoop },
0x00E6: { n:"BrtEndPCDSDTCEntries", f:parsenoop },
0x00E7: { n:"BrtBeginPCDSDTCEMembers", f:parsenoop },
0x00E8: { n:"BrtEndPCDSDTCEMembers", f:parsenoop },
0x00E9: { n:"BrtBeginPCDSDTCEMember", f:parsenoop },
0x00EA: { n:"BrtEndPCDSDTCEMember", f:parsenoop },
0x00EB: { n:"BrtBeginPCDSDTCQueries", f:parsenoop },
0x00EC: { n:"BrtEndPCDSDTCQueries", f:parsenoop },
0x00ED: { n:"BrtBeginPCDSDTCQuery", f:parsenoop },
0x00EE: { n:"BrtEndPCDSDTCQuery", f:parsenoop },
0x00EF: { n:"BrtBeginPCDSDTCSets", f:parsenoop },
0x00F0: { n:"BrtEndPCDSDTCSets", f:parsenoop },
0x00F1: { n:"BrtBeginPCDSDTCSet", f:parsenoop },
0x00F2: { n:"BrtEndPCDSDTCSet", f:parsenoop },
0x00F3: { n:"BrtBeginPCDCalcItems", f:parsenoop },
0x00F4: { n:"BrtEndPCDCalcItems", f:parsenoop },
0x00F5: { n:"BrtBeginPCDCalcItem", f:parsenoop },
0x00F6: { n:"BrtEndPCDCalcItem", f:parsenoop },
0x00F7: { n:"BrtBeginPRule", f:parsenoop },
0x00F8: { n:"BrtEndPRule", f:parsenoop },
0x00F9: { n:"BrtBeginPRFilters", f:parsenoop },
0x00FA: { n:"BrtEndPRFilters", f:parsenoop },
0x00FB: { n:"BrtBeginPRFilter", f:parsenoop },
0x00FC: { n:"BrtEndPRFilter", f:parsenoop },
0x00FD: { n:"BrtBeginPNames", f:parsenoop },
0x00FE: { n:"BrtEndPNames", f:parsenoop },
0x00FF: { n:"BrtBeginPName", f:parsenoop },
0x0100: { n:"BrtEndPName", f:parsenoop },
0x0101: { n:"BrtBeginPNPairs", f:parsenoop },
0x0102: { n:"BrtEndPNPairs", f:parsenoop },
0x0103: { n:"BrtBeginPNPair", f:parsenoop },
0x0104: { n:"BrtEndPNPair", f:parsenoop },
0x0105: { n:"BrtBeginECWebProps", f:parsenoop },
0x0106: { n:"BrtEndECWebProps", f:parsenoop },
0x0107: { n:"BrtBeginEcWpTables", f:parsenoop },
0x0108: { n:"BrtEndECWPTables", f:parsenoop },
0x0109: { n:"BrtBeginECParams", f:parsenoop },
0x010A: { n:"BrtEndECParams", f:parsenoop },
0x010B: { n:"BrtBeginECParam", f:parsenoop },
0x010C: { n:"BrtEndECParam", f:parsenoop },
0x010D: { n:"BrtBeginPCDKPIs", f:parsenoop },
0x010E: { n:"BrtEndPCDKPIs", f:parsenoop },
0x010F: { n:"BrtBeginPCDKPI", f:parsenoop },
0x0110: { n:"BrtEndPCDKPI", f:parsenoop },
0x0111: { n:"BrtBeginDims", f:parsenoop },
0x0112: { n:"BrtEndDims", f:parsenoop },
0x0113: { n:"BrtBeginDim", f:parsenoop },
0x0114: { n:"BrtEndDim", f:parsenoop },
0x0115: { n:"BrtIndexPartEnd", f:parsenoop },
0x0116: { n:"BrtBeginStyleSheet", f:parsenoop },
0x0117: { n:"BrtEndStyleSheet", f:parsenoop },
0x0118: { n:"BrtBeginSXView", f:parsenoop },
0x0119: { n:"BrtEndSXVI", f:parsenoop },
0x011A: { n:"BrtBeginSXVI", f:parsenoop },
0x011B: { n:"BrtBeginSXVIs", f:parsenoop },
0x011C: { n:"BrtEndSXVIs", f:parsenoop },
0x011D: { n:"BrtBeginSXVD", f:parsenoop },
0x011E: { n:"BrtEndSXVD", f:parsenoop },
0x011F: { n:"BrtBeginSXVDs", f:parsenoop },
0x0120: { n:"BrtEndSXVDs", f:parsenoop },
0x0121: { n:"BrtBeginSXPI", f:parsenoop },
0x0122: { n:"BrtEndSXPI", f:parsenoop },
0x0123: { n:"BrtBeginSXPIs", f:parsenoop },
0x0124: { n:"BrtEndSXPIs", f:parsenoop },
0x0125: { n:"BrtBeginSXDI", f:parsenoop },
0x0126: { n:"BrtEndSXDI", f:parsenoop },
0x0127: { n:"BrtBeginSXDIs", f:parsenoop },
0x0128: { n:"BrtEndSXDIs", f:parsenoop },
0x0129: { n:"BrtBeginSXLI", f:parsenoop },
0x012A: { n:"BrtEndSXLI", f:parsenoop },
0x012B: { n:"BrtBeginSXLIRws", f:parsenoop },
0x012C: { n:"BrtEndSXLIRws", f:parsenoop },
0x012D: { n:"BrtBeginSXLICols", f:parsenoop },
0x012E: { n:"BrtEndSXLICols", f:parsenoop },
0x012F: { n:"BrtBeginSXFormat", f:parsenoop },
0x0130: { n:"BrtEndSXFormat", f:parsenoop },
0x0131: { n:"BrtBeginSXFormats", f:parsenoop },
0x0132: { n:"BrtEndSxFormats", f:parsenoop },
0x0133: { n:"BrtBeginSxSelect", f:parsenoop },
0x0134: { n:"BrtEndSxSelect", f:parsenoop },
0x0135: { n:"BrtBeginISXVDRws", f:parsenoop },
0x0136: { n:"BrtEndISXVDRws", f:parsenoop },
0x0137: { n:"BrtBeginISXVDCols", f:parsenoop },
0x0138: { n:"BrtEndISXVDCols", f:parsenoop },
0x0139: { n:"BrtEndSXLocation", f:parsenoop },
0x013A: { n:"BrtBeginSXLocation", f:parsenoop },
0x013B: { n:"BrtEndSXView", f:parsenoop },
0x013C: { n:"BrtBeginSXTHs", f:parsenoop },
0x013D: { n:"BrtEndSXTHs", f:parsenoop },
0x013E: { n:"BrtBeginSXTH", f:parsenoop },
0x013F: { n:"BrtEndSXTH", f:parsenoop },
0x0140: { n:"BrtBeginISXTHRws", f:parsenoop },
0x0141: { n:"BrtEndISXTHRws", f:parsenoop },
0x0142: { n:"BrtBeginISXTHCols", f:parsenoop },
0x0143: { n:"BrtEndISXTHCols", f:parsenoop },
0x0144: { n:"BrtBeginSXTDMPS", f:parsenoop },
0x0145: { n:"BrtEndSXTDMPs", f:parsenoop },
0x0146: { n:"BrtBeginSXTDMP", f:parsenoop },
0x0147: { n:"BrtEndSXTDMP", f:parsenoop },
0x0148: { n:"BrtBeginSXTHItems", f:parsenoop },
0x0149: { n:"BrtEndSXTHItems", f:parsenoop },
0x014A: { n:"BrtBeginSXTHItem", f:parsenoop },
0x014B: { n:"BrtEndSXTHItem", f:parsenoop },
0x014C: { n:"BrtBeginMetadata", f:parsenoop },
0x014D: { n:"BrtEndMetadata", f:parsenoop },
0x014E: { n:"BrtBeginEsmdtinfo", f:parsenoop },
0x014F: { n:"BrtMdtinfo", f:parsenoop },
0x0150: { n:"BrtEndEsmdtinfo", f:parsenoop },
0x0151: { n:"BrtBeginEsmdb", f:parsenoop },
0x0152: { n:"BrtEndEsmdb", f:parsenoop },
0x0153: { n:"BrtBeginEsfmd", f:parsenoop },
0x0154: { n:"BrtEndEsfmd", f:parsenoop },
0x0155: { n:"BrtBeginSingleCells", f:parsenoop },
0x0156: { n:"BrtEndSingleCells", f:parsenoop },
0x0157: { n:"BrtBeginList", f:parsenoop },
0x0158: { n:"BrtEndList", f:parsenoop },
0x0159: { n:"BrtBeginListCols", f:parsenoop },
0x015A: { n:"BrtEndListCols", f:parsenoop },
0x015B: { n:"BrtBeginListCol", f:parsenoop },
0x015C: { n:"BrtEndListCol", f:parsenoop },
0x015D: { n:"BrtBeginListXmlCPr", f:parsenoop },
0x015E: { n:"BrtEndListXmlCPr", f:parsenoop },
0x015F: { n:"BrtListCCFmla", f:parsenoop },
0x0160: { n:"BrtListTrFmla", f:parsenoop },
0x0161: { n:"BrtBeginExternals", f:parsenoop },
0x0162: { n:"BrtEndExternals", f:parsenoop },
0x0163: { n:"BrtSupBookSrc", f:parsenoop },
0x0165: { n:"BrtSupSelf", f:parsenoop },
0x0166: { n:"BrtSupSame", f:parsenoop },
0x0167: { n:"BrtSupTabs", f:parsenoop },
0x0168: { n:"BrtBeginSupBook", f:parsenoop },
0x0169: { n:"BrtPlaceholderName", f:parsenoop },
0x016A: { n:"BrtExternSheet", f:parsenoop },
0x016B: { n:"BrtExternTableStart", f:parsenoop },
0x016C: { n:"BrtExternTableEnd", f:parsenoop },
0x016E: { n:"BrtExternRowHdr", f:parsenoop },
0x016F: { n:"BrtExternCellBlank", f:parsenoop },
0x0170: { n:"BrtExternCellReal", f:parsenoop },
0x0171: { n:"BrtExternCellBool", f:parsenoop },
0x0172: { n:"BrtExternCellError", f:parsenoop },
0x0173: { n:"BrtExternCellString", f:parsenoop },
0x0174: { n:"BrtBeginEsmdx", f:parsenoop },
0x0175: { n:"BrtEndEsmdx", f:parsenoop },
0x0176: { n:"BrtBeginMdxSet", f:parsenoop },
0x0177: { n:"BrtEndMdxSet", f:parsenoop },
0x0178: { n:"BrtBeginMdxMbrProp", f:parsenoop },
0x0179: { n:"BrtEndMdxMbrProp", f:parsenoop },
0x017A: { n:"BrtBeginMdxKPI", f:parsenoop },
0x017B: { n:"BrtEndMdxKPI", f:parsenoop },
0x017C: { n:"BrtBeginEsstr", f:parsenoop },
0x017D: { n:"BrtEndEsstr", f:parsenoop },
0x017E: { n:"BrtBeginPRFItem", f:parsenoop },
0x017F: { n:"BrtEndPRFItem", f:parsenoop },
0x0180: { n:"BrtBeginPivotCacheIDs", f:parsenoop },
0x0181: { n:"BrtEndPivotCacheIDs", f:parsenoop },
0x0182: { n:"BrtBeginPivotCacheID", f:parsenoop },
0x0183: { n:"BrtEndPivotCacheID", f:parsenoop },
0x0184: { n:"BrtBeginISXVIs", f:parsenoop },
0x0185: { n:"BrtEndISXVIs", f:parsenoop },
0x0186: { n:"BrtBeginColInfos", f:parsenoop },
0x0187: { n:"BrtEndColInfos", f:parsenoop },
0x0188: { n:"BrtBeginRwBrk", f:parsenoop },
0x0189: { n:"BrtEndRwBrk", f:parsenoop },
0x018A: { n:"BrtBeginColBrk", f:parsenoop },
0x018B: { n:"BrtEndColBrk", f:parsenoop },
0x018C: { n:"BrtBrk", f:parsenoop },
0x018D: { n:"BrtUserBookView", f:parsenoop },
0x018E: { n:"BrtInfo", f:parsenoop },
0x018F: { n:"BrtCUsr", f:parsenoop },
0x0190: { n:"BrtUsr", f:parsenoop },
0x0191: { n:"BrtBeginUsers", f:parsenoop },
0x0193: { n:"BrtEOF", f:parsenoop },
0x0194: { n:"BrtUCR", f:parsenoop },
0x0195: { n:"BrtRRInsDel", f:parsenoop },
0x0196: { n:"BrtRREndInsDel", f:parsenoop },
0x0197: { n:"BrtRRMove", f:parsenoop },
0x0198: { n:"BrtRREndMove", f:parsenoop },
0x0199: { n:"BrtRRChgCell", f:parsenoop },
0x019A: { n:"BrtRREndChgCell", f:parsenoop },
0x019B: { n:"BrtRRHeader", f:parsenoop },
0x019C: { n:"BrtRRUserView", f:parsenoop },
0x019D: { n:"BrtRRRenSheet", f:parsenoop },
0x019E: { n:"BrtRRInsertSh", f:parsenoop },
0x019F: { n:"BrtRRDefName", f:parsenoop },
0x01A0: { n:"BrtRRNote", f:parsenoop },
0x01A1: { n:"BrtRRConflict", f:parsenoop },
0x01A2: { n:"BrtRRTQSIF", f:parsenoop },
0x01A3: { n:"BrtRRFormat", f:parsenoop },
0x01A4: { n:"BrtRREndFormat", f:parsenoop },
0x01A5: { n:"BrtRRAutoFmt", f:parsenoop },
0x01A6: { n:"BrtBeginUserShViews", f:parsenoop },
0x01A7: { n:"BrtBeginUserShView", f:parsenoop },
0x01A8: { n:"BrtEndUserShView", f:parsenoop },
0x01A9: { n:"BrtEndUserShViews", f:parsenoop },
0x01AA: { n:"BrtArrFmla", f:parse_BrtArrFmla },
0x01AB: { n:"BrtShrFmla", f:parse_BrtShrFmla },
0x01AC: { n:"BrtTable", f:parsenoop },
0x01AD: { n:"BrtBeginExtConnections", f:parsenoop },
0x01AE: { n:"BrtEndExtConnections", f:parsenoop },
0x01AF: { n:"BrtBeginPCDCalcMems", f:parsenoop },
0x01B0: { n:"BrtEndPCDCalcMems", f:parsenoop },
0x01B1: { n:"BrtBeginPCDCalcMem", f:parsenoop },
0x01B2: { n:"BrtEndPCDCalcMem", f:parsenoop },
0x01B3: { n:"BrtBeginPCDHGLevels", f:parsenoop },
0x01B4: { n:"BrtEndPCDHGLevels", f:parsenoop },
0x01B5: { n:"BrtBeginPCDHGLevel", f:parsenoop },
0x01B6: { n:"BrtEndPCDHGLevel", f:parsenoop },
0x01B7: { n:"BrtBeginPCDHGLGroups", f:parsenoop },
0x01B8: { n:"BrtEndPCDHGLGroups", f:parsenoop },
0x01B9: { n:"BrtBeginPCDHGLGroup", f:parsenoop },
0x01BA: { n:"BrtEndPCDHGLGroup", f:parsenoop },
0x01BB: { n:"BrtBeginPCDHGLGMembers", f:parsenoop },
0x01BC: { n:"BrtEndPCDHGLGMembers", f:parsenoop },
0x01BD: { n:"BrtBeginPCDHGLGMember", f:parsenoop },
0x01BE: { n:"BrtEndPCDHGLGMember", f:parsenoop },
0x01BF: { n:"BrtBeginQSI", f:parsenoop },
0x01C0: { n:"BrtEndQSI", f:parsenoop },
0x01C1: { n:"BrtBeginQSIR", f:parsenoop },
0x01C2: { n:"BrtEndQSIR", f:parsenoop },
0x01C3: { n:"BrtBeginDeletedNames", f:parsenoop },
0x01C4: { n:"BrtEndDeletedNames", f:parsenoop },
0x01C5: { n:"BrtBeginDeletedName", f:parsenoop },
0x01C6: { n:"BrtEndDeletedName", f:parsenoop },
0x01C7: { n:"BrtBeginQSIFs", f:parsenoop },
0x01C8: { n:"BrtEndQSIFs", f:parsenoop },
0x01C9: { n:"BrtBeginQSIF", f:parsenoop },
0x01CA: { n:"BrtEndQSIF", f:parsenoop },
0x01CB: { n:"BrtBeginAutoSortScope", f:parsenoop },
0x01CC: { n:"BrtEndAutoSortScope", f:parsenoop },
0x01CD: { n:"BrtBeginConditionalFormatting", f:parsenoop },
0x01CE: { n:"BrtEndConditionalFormatting", f:parsenoop },
0x01CF: { n:"BrtBeginCFRule", f:parsenoop },
0x01D0: { n:"BrtEndCFRule", f:parsenoop },
0x01D1: { n:"BrtBeginIconSet", f:parsenoop },
0x01D2: { n:"BrtEndIconSet", f:parsenoop },
0x01D3: { n:"BrtBeginDatabar", f:parsenoop },
0x01D4: { n:"BrtEndDatabar", f:parsenoop },
0x01D5: { n:"BrtBeginColorScale", f:parsenoop },
0x01D6: { n:"BrtEndColorScale", f:parsenoop },
0x01D7: { n:"BrtCFVO", f:parsenoop },
0x01D8: { n:"BrtExternValueMeta", f:parsenoop },
0x01D9: { n:"BrtBeginColorPalette", f:parsenoop },
0x01DA: { n:"BrtEndColorPalette", f:parsenoop },
0x01DB: { n:"BrtIndexedColor", f:parsenoop },
0x01DC: { n:"BrtMargins", f:parse_BrtMargins },
0x01DD: { n:"BrtPrintOptions", f:parsenoop },
0x01DE: { n:"BrtPageSetup", f:parsenoop },
0x01DF: { n:"BrtBeginHeaderFooter", f:parsenoop },
0x01E0: { n:"BrtEndHeaderFooter", f:parsenoop },
0x01E1: { n:"BrtBeginSXCrtFormat", f:parsenoop },
0x01E2: { n:"BrtEndSXCrtFormat", f:parsenoop },
0x01E3: { n:"BrtBeginSXCrtFormats", f:parsenoop },
0x01E4: { n:"BrtEndSXCrtFormats", f:parsenoop },
0x01E5: { n:"BrtWsFmtInfo", f:parsenoop },
0x01E6: { n:"BrtBeginMgs", f:parsenoop },
0x01E7: { n:"BrtEndMGs", f:parsenoop },
0x01E8: { n:"BrtBeginMGMaps", f:parsenoop },
0x01E9: { n:"BrtEndMGMaps", f:parsenoop },
0x01EA: { n:"BrtBeginMG", f:parsenoop },
0x01EB: { n:"BrtEndMG", f:parsenoop },
0x01EC: { n:"BrtBeginMap", f:parsenoop },
0x01ED: { n:"BrtEndMap", f:parsenoop },
0x01EE: { n:"BrtHLink", f:parse_BrtHLink },
0x01EF: { n:"BrtBeginDCon", f:parsenoop },
0x01F0: { n:"BrtEndDCon", f:parsenoop },
0x01F1: { n:"BrtBeginDRefs", f:parsenoop },
0x01F2: { n:"BrtEndDRefs", f:parsenoop },
0x01F3: { n:"BrtDRef", f:parsenoop },
0x01F4: { n:"BrtBeginScenMan", f:parsenoop },
0x01F5: { n:"BrtEndScenMan", f:parsenoop },
0x01F6: { n:"BrtBeginSct", f:parsenoop },
0x01F7: { n:"BrtEndSct", f:parsenoop },
0x01F8: { n:"BrtSlc", f:parsenoop },
0x01F9: { n:"BrtBeginDXFs", f:parsenoop },
0x01FA: { n:"BrtEndDXFs", f:parsenoop },
0x01FB: { n:"BrtDXF", f:parsenoop },
0x01FC: { n:"BrtBeginTableStyles", f:parsenoop },
0x01FD: { n:"BrtEndTableStyles", f:parsenoop },
0x01FE: { n:"BrtBeginTableStyle", f:parsenoop },
0x01FF: { n:"BrtEndTableStyle", f:parsenoop },
0x0200: { n:"BrtTableStyleElement", f:parsenoop },
0x0201: { n:"BrtTableStyleClient", f:parsenoop },
0x0202: { n:"BrtBeginVolDeps", f:parsenoop },
0x0203: { n:"BrtEndVolDeps", f:parsenoop },
0x0204: { n:"BrtBeginVolType", f:parsenoop },
0x0205: { n:"BrtEndVolType", f:parsenoop },
0x0206: { n:"BrtBeginVolMain", f:parsenoop },
0x0207: { n:"BrtEndVolMain", f:parsenoop },
0x0208: { n:"BrtBeginVolTopic", f:parsenoop },
0x0209: { n:"BrtEndVolTopic", f:parsenoop },
0x020A: { n:"BrtVolSubtopic", f:parsenoop },
0x020B: { n:"BrtVolRef", f:parsenoop },
0x020C: { n:"BrtVolNum", f:parsenoop },
0x020D: { n:"BrtVolErr", f:parsenoop },
0x020E: { n:"BrtVolStr", f:parsenoop },
0x020F: { n:"BrtVolBool", f:parsenoop },
0x0210: { n:"BrtBeginCalcChain$", f:parsenoop },
0x0211: { n:"BrtEndCalcChain$", f:parsenoop },
0x0212: { n:"BrtBeginSortState", f:parsenoop },
0x0213: { n:"BrtEndSortState", f:parsenoop },
0x0214: { n:"BrtBeginSortCond", f:parsenoop },
0x0215: { n:"BrtEndSortCond", f:parsenoop },
0x0216: { n:"BrtBookProtection", f:parsenoop },
0x0217: { n:"BrtSheetProtection", f:parsenoop },
0x0218: { n:"BrtRangeProtection", f:parsenoop },
0x0219: { n:"BrtPhoneticInfo", f:parsenoop },
0x021A: { n:"BrtBeginECTxtWiz", f:parsenoop },
0x021B: { n:"BrtEndECTxtWiz", f:parsenoop },
0x021C: { n:"BrtBeginECTWFldInfoLst", f:parsenoop },
0x021D: { n:"BrtEndECTWFldInfoLst", f:parsenoop },
0x021E: { n:"BrtBeginECTwFldInfo", f:parsenoop },
0x0224: { n:"BrtFileSharing", f:parsenoop },
0x0225: { n:"BrtOleSize", f:parsenoop },
0x0226: { n:"BrtDrawing", f:parse_RelID },
0x0227: { n:"BrtLegacyDrawing", f:parsenoop },
0x0228: { n:"BrtLegacyDrawingHF", f:parsenoop },
0x0229: { n:"BrtWebOpt", f:parsenoop },
0x022A: { n:"BrtBeginWebPubItems", f:parsenoop },
0x022B: { n:"BrtEndWebPubItems", f:parsenoop },
0x022C: { n:"BrtBeginWebPubItem", f:parsenoop },
0x022D: { n:"BrtEndWebPubItem", f:parsenoop },
0x022E: { n:"BrtBeginSXCondFmt", f:parsenoop },
0x022F: { n:"BrtEndSXCondFmt", f:parsenoop },
0x0230: { n:"BrtBeginSXCondFmts", f:parsenoop },
0x0231: { n:"BrtEndSXCondFmts", f:parsenoop },
0x0232: { n:"BrtBkHim", f:parsenoop },
0x0234: { n:"BrtColor", f:parsenoop },
0x0235: { n:"BrtBeginIndexedColors", f:parsenoop },
0x0236: { n:"BrtEndIndexedColors", f:parsenoop },
0x0239: { n:"BrtBeginMRUColors", f:parsenoop },
0x023A: { n:"BrtEndMRUColors", f:parsenoop },
0x023C: { n:"BrtMRUColor", f:parsenoop },
0x023D: { n:"BrtBeginDVals", f:parsenoop },
0x023E: { n:"BrtEndDVals", f:parsenoop },
0x0241: { n:"BrtSupNameStart", f:parsenoop },
0x0242: { n:"BrtSupNameValueStart", f:parsenoop },
0x0243: { n:"BrtSupNameValueEnd", f:parsenoop },
0x0244: { n:"BrtSupNameNum", f:parsenoop },
0x0245: { n:"BrtSupNameErr", f:parsenoop },
0x0246: { n:"BrtSupNameSt", f:parsenoop },
0x0247: { n:"BrtSupNameNil", f:parsenoop },
0x0248: { n:"BrtSupNameBool", f:parsenoop },
0x0249: { n:"BrtSupNameFmla", f:parsenoop },
0x024A: { n:"BrtSupNameBits", f:parsenoop },
0x024B: { n:"BrtSupNameEnd", f:parsenoop },
0x024C: { n:"BrtEndSupBook", f:parsenoop },
0x024D: { n:"BrtCellSmartTagProperty", f:parsenoop },
0x024E: { n:"BrtBeginCellSmartTag", f:parsenoop },
0x024F: { n:"BrtEndCellSmartTag", f:parsenoop },
0x0250: { n:"BrtBeginCellSmartTags", f:parsenoop },
0x0251: { n:"BrtEndCellSmartTags", f:parsenoop },
0x0252: { n:"BrtBeginSmartTags", f:parsenoop },
0x0253: { n:"BrtEndSmartTags", f:parsenoop },
0x0254: { n:"BrtSmartTagType", f:parsenoop },
0x0255: { n:"BrtBeginSmartTagTypes", f:parsenoop },
0x0256: { n:"BrtEndSmartTagTypes", f:parsenoop },
0x0257: { n:"BrtBeginSXFilters", f:parsenoop },
0x0258: { n:"BrtEndSXFilters", f:parsenoop },
0x0259: { n:"BrtBeginSXFILTER", f:parsenoop },
0x025A: { n:"BrtEndSXFilter", f:parsenoop },
0x025B: { n:"BrtBeginFills", f:parsenoop },
0x025C: { n:"BrtEndFills", f:parsenoop },
0x025D: { n:"BrtBeginCellWatches", f:parsenoop },
0x025E: { n:"BrtEndCellWatches", f:parsenoop },
0x025F: { n:"BrtCellWatch", f:parsenoop },
0x0260: { n:"BrtBeginCRErrs", f:parsenoop },
0x0261: { n:"BrtEndCRErrs", f:parsenoop },
0x0262: { n:"BrtCrashRecErr", f:parsenoop },
0x0263: { n:"BrtBeginFonts", f:parsenoop },
0x0264: { n:"BrtEndFonts", f:parsenoop },
0x0265: { n:"BrtBeginBorders", f:parsenoop },
0x0266: { n:"BrtEndBorders", f:parsenoop },
0x0267: { n:"BrtBeginFmts", f:parsenoop },
0x0268: { n:"BrtEndFmts", f:parsenoop },
0x0269: { n:"BrtBeginCellXFs", f:parsenoop },
0x026A: { n:"BrtEndCellXFs", f:parsenoop },
0x026B: { n:"BrtBeginStyles", f:parsenoop },
0x026C: { n:"BrtEndStyles", f:parsenoop },
0x0271: { n:"BrtBigName", f:parsenoop },
0x0272: { n:"BrtBeginCellStyleXFs", f:parsenoop },
0x0273: { n:"BrtEndCellStyleXFs", f:parsenoop },
0x0274: { n:"BrtBeginComments", f:parsenoop },
0x0275: { n:"BrtEndComments", f:parsenoop },
0x0276: { n:"BrtBeginCommentAuthors", f:parsenoop },
0x0277: { n:"BrtEndCommentAuthors", f:parsenoop },
0x0278: { n:"BrtCommentAuthor", f:parse_BrtCommentAuthor },
0x0279: { n:"BrtBeginCommentList", f:parsenoop },
0x027A: { n:"BrtEndCommentList", f:parsenoop },
0x027B: { n:"BrtBeginComment", f:parse_BrtBeginComment},
0x027C: { n:"BrtEndComment", f:parsenoop },
0x027D: { n:"BrtCommentText", f:parse_BrtCommentText },
0x027E: { n:"BrtBeginOleObjects", f:parsenoop },
0x027F: { n:"BrtOleObject", f:parsenoop },
0x0280: { n:"BrtEndOleObjects", f:parsenoop },
0x0281: { n:"BrtBeginSxrules", f:parsenoop },
0x0282: { n:"BrtEndSxRules", f:parsenoop },
0x0283: { n:"BrtBeginActiveXControls", f:parsenoop },
0x0284: { n:"BrtActiveX", f:parsenoop },
0x0285: { n:"BrtEndActiveXControls", f:parsenoop },
0x0286: { n:"BrtBeginPCDSDTCEMembersSortBy", f:parsenoop },
0x0288: { n:"BrtBeginCellIgnoreECs", f:parsenoop },
0x0289: { n:"BrtCellIgnoreEC", f:parsenoop },
0x028A: { n:"BrtEndCellIgnoreECs", f:parsenoop },
0x028B: { n:"BrtCsProp", f:parsenoop },
0x028C: { n:"BrtCsPageSetup", f:parsenoop },
0x028D: { n:"BrtBeginUserCsViews", f:parsenoop },
0x028E: { n:"BrtEndUserCsViews", f:parsenoop },
0x028F: { n:"BrtBeginUserCsView", f:parsenoop },
0x0290: { n:"BrtEndUserCsView", f:parsenoop },
0x0291: { n:"BrtBeginPcdSFCIEntries", f:parsenoop },
0x0292: { n:"BrtEndPCDSFCIEntries", f:parsenoop },
0x0293: { n:"BrtPCDSFCIEntry", f:parsenoop },
0x0294: { n:"BrtBeginListParts", f:parsenoop },
0x0295: { n:"BrtListPart", f:parsenoop },
0x0296: { n:"BrtEndListParts", f:parsenoop },
0x0297: { n:"BrtSheetCalcProp", f:parsenoop },
0x0298: { n:"BrtBeginFnGroup", f:parsenoop },
0x0299: { n:"BrtFnGroup", f:parsenoop },
0x029A: { n:"BrtEndFnGroup", f:parsenoop },
0x029B: { n:"BrtSupAddin", f:parsenoop },
0x029C: { n:"BrtSXTDMPOrder", f:parsenoop },
0x029D: { n:"BrtCsProtection", f:parsenoop },
0x029F: { n:"BrtBeginWsSortMap", f:parsenoop },
0x02A0: { n:"BrtEndWsSortMap", f:parsenoop },
0x02A1: { n:"BrtBeginRRSort", f:parsenoop },
0x02A2: { n:"BrtEndRRSort", f:parsenoop },
0x02A3: { n:"BrtRRSortItem", f:parsenoop },
0x02A4: { n:"BrtFileSharingIso", f:parsenoop },
0x02A5: { n:"BrtBookProtectionIso", f:parsenoop },
0x02A6: { n:"BrtSheetProtectionIso", f:parsenoop },
0x02A7: { n:"BrtCsProtectionIso", f:parsenoop },
0x02A8: { n:"BrtRangeProtectionIso", f:parsenoop },
0x0400: { n:"BrtRwDescent", f:parsenoop },
0x0401: { n:"BrtKnownFonts", f:parsenoop },
0x0402: { n:"BrtBeginSXTupleSet", f:parsenoop },
0x0403: { n:"BrtEndSXTupleSet", f:parsenoop },
0x0404: { n:"BrtBeginSXTupleSetHeader", f:parsenoop },
0x0405: { n:"BrtEndSXTupleSetHeader", f:parsenoop },
0x0406: { n:"BrtSXTupleSetHeaderItem", f:parsenoop },
0x0407: { n:"BrtBeginSXTupleSetData", f:parsenoop },
0x0408: { n:"BrtEndSXTupleSetData", f:parsenoop },
0x0409: { n:"BrtBeginSXTupleSetRow", f:parsenoop },
0x040A: { n:"BrtEndSXTupleSetRow", f:parsenoop },
0x040B: { n:"BrtSXTupleSetRowItem", f:parsenoop },
0x040C: { n:"BrtNameExt", f:parsenoop },
0x040D: { n:"BrtPCDH14", f:parsenoop },
0x040E: { n:"BrtBeginPCDCalcMem14", f:parsenoop },
0x040F: { n:"BrtEndPCDCalcMem14", f:parsenoop },
0x0410: { n:"BrtSXTH14", f:parsenoop },
0x0411: { n:"BrtBeginSparklineGroup", f:parsenoop },
0x0412: { n:"BrtEndSparklineGroup", f:parsenoop },
0x0413: { n:"BrtSparkline", f:parsenoop },
0x0414: { n:"BrtSXDI14", f:parsenoop },
0x0415: { n:"BrtWsFmtInfoEx14", f:parsenoop },
0x0416: { n:"BrtBeginConditionalFormatting14", f:parsenoop },
0x0417: { n:"BrtEndConditionalFormatting14", f:parsenoop },
0x0418: { n:"BrtBeginCFRule14", f:parsenoop },
0x0419: { n:"BrtEndCFRule14", f:parsenoop },
0x041A: { n:"BrtCFVO14", f:parsenoop },
0x041B: { n:"BrtBeginDatabar14", f:parsenoop },
0x041C: { n:"BrtBeginIconSet14", f:parsenoop },
0x041D: { n:"BrtDVal14", f:parsenoop },
0x041E: { n:"BrtBeginDVals14", f:parsenoop },
0x041F: { n:"BrtColor14", f:parsenoop },
0x0420: { n:"BrtBeginSparklines", f:parsenoop },
0x0421: { n:"BrtEndSparklines", f:parsenoop },
0x0422: { n:"BrtBeginSparklineGroups", f:parsenoop },
0x0423: { n:"BrtEndSparklineGroups", f:parsenoop },
0x0425: { n:"BrtSXVD14", f:parsenoop },
0x0426: { n:"BrtBeginSxview14", f:parsenoop },
0x0427: { n:"BrtEndSxview14", f:parsenoop },
0x042A: { n:"BrtBeginPCD14", f:parsenoop },
0x042B: { n:"BrtEndPCD14", f:parsenoop },
0x042C: { n:"BrtBeginExtConn14", f:parsenoop },
0x042D: { n:"BrtEndExtConn14", f:parsenoop },
0x042E: { n:"BrtBeginSlicerCacheIDs", f:parsenoop },
0x042F: { n:"BrtEndSlicerCacheIDs", f:parsenoop },
0x0430: { n:"BrtBeginSlicerCacheID", f:parsenoop },
0x0431: { n:"BrtEndSlicerCacheID", f:parsenoop },
0x0433: { n:"BrtBeginSlicerCache", f:parsenoop },
0x0434: { n:"BrtEndSlicerCache", f:parsenoop },
0x0435: { n:"BrtBeginSlicerCacheDef", f:parsenoop },
0x0436: { n:"BrtEndSlicerCacheDef", f:parsenoop },
0x0437: { n:"BrtBeginSlicersEx", f:parsenoop },
0x0438: { n:"BrtEndSlicersEx", f:parsenoop },
0x0439: { n:"BrtBeginSlicerEx", f:parsenoop },
0x043A: { n:"BrtEndSlicerEx", f:parsenoop },
0x043B: { n:"BrtBeginSlicer", f:parsenoop },
0x043C: { n:"BrtEndSlicer", f:parsenoop },
0x043D: { n:"BrtSlicerCachePivotTables", f:parsenoop },
0x043E: { n:"BrtBeginSlicerCacheOlapImpl", f:parsenoop },
0x043F: { n:"BrtEndSlicerCacheOlapImpl", f:parsenoop },
0x0440: { n:"BrtBeginSlicerCacheLevelsData", f:parsenoop },
0x0441: { n:"BrtEndSlicerCacheLevelsData", f:parsenoop },
0x0442: { n:"BrtBeginSlicerCacheLevelData", f:parsenoop },
0x0443: { n:"BrtEndSlicerCacheLevelData", f:parsenoop },
0x0444: { n:"BrtBeginSlicerCacheSiRanges", f:parsenoop },
0x0445: { n:"BrtEndSlicerCacheSiRanges", f:parsenoop },
0x0446: { n:"BrtBeginSlicerCacheSiRange", f:parsenoop },
0x0447: { n:"BrtEndSlicerCacheSiRange", f:parsenoop },
0x0448: { n:"BrtSlicerCacheOlapItem", f:parsenoop },
0x0449: { n:"BrtBeginSlicerCacheSelections", f:parsenoop },
0x044A: { n:"BrtSlicerCacheSelection", f:parsenoop },
0x044B: { n:"BrtEndSlicerCacheSelections", f:parsenoop },
0x044C: { n:"BrtBeginSlicerCacheNative", f:parsenoop },
0x044D: { n:"BrtEndSlicerCacheNative", f:parsenoop },
0x044E: { n:"BrtSlicerCacheNativeItem", f:parsenoop },
0x044F: { n:"BrtRangeProtection14", f:parsenoop },
0x0450: { n:"BrtRangeProtectionIso14", f:parsenoop },
0x0451: { n:"BrtCellIgnoreEC14", f:parsenoop },
0x0457: { n:"BrtList14", f:parsenoop },
0x0458: { n:"BrtCFIcon", f:parsenoop },
0x0459: { n:"BrtBeginSlicerCachesPivotCacheIDs", f:parsenoop },
0x045A: { n:"BrtEndSlicerCachesPivotCacheIDs", f:parsenoop },
0x045B: { n:"BrtBeginSlicers", f:parsenoop },
0x045C: { n:"BrtEndSlicers", f:parsenoop },
0x045D: { n:"BrtWbProp14", f:parsenoop },
0x045E: { n:"BrtBeginSXEdit", f:parsenoop },
0x045F: { n:"BrtEndSXEdit", f:parsenoop },
0x0460: { n:"BrtBeginSXEdits", f:parsenoop },
0x0461: { n:"BrtEndSXEdits", f:parsenoop },
0x0462: { n:"BrtBeginSXChange", f:parsenoop },
0x0463: { n:"BrtEndSXChange", f:parsenoop },
0x0464: { n:"BrtBeginSXChanges", f:parsenoop },
0x0465: { n:"BrtEndSXChanges", f:parsenoop },
0x0466: { n:"BrtSXTupleItems", f:parsenoop },
0x0468: { n:"BrtBeginSlicerStyle", f:parsenoop },
0x0469: { n:"BrtEndSlicerStyle", f:parsenoop },
0x046A: { n:"BrtSlicerStyleElement", f:parsenoop },
0x046B: { n:"BrtBeginStyleSheetExt14", f:parsenoop },
0x046C: { n:"BrtEndStyleSheetExt14", f:parsenoop },
0x046D: { n:"BrtBeginSlicerCachesPivotCacheID", f:parsenoop },
0x046E: { n:"BrtEndSlicerCachesPivotCacheID", f:parsenoop },
0x046F: { n:"BrtBeginConditionalFormattings", f:parsenoop },
0x0470: { n:"BrtEndConditionalFormattings", f:parsenoop },
0x0471: { n:"BrtBeginPCDCalcMemExt", f:parsenoop },
0x0472: { n:"BrtEndPCDCalcMemExt", f:parsenoop },
0x0473: { n:"BrtBeginPCDCalcMemsExt", f:parsenoop },
0x0474: { n:"BrtEndPCDCalcMemsExt", f:parsenoop },
0x0475: { n:"BrtPCDField14", f:parsenoop },
0x0476: { n:"BrtBeginSlicerStyles", f:parsenoop },
0x0477: { n:"BrtEndSlicerStyles", f:parsenoop },
0x0478: { n:"BrtBeginSlicerStyleElements", f:parsenoop },
0x0479: { n:"BrtEndSlicerStyleElements", f:parsenoop },
0x047A: { n:"BrtCFRuleExt", f:parsenoop },
0x047B: { n:"BrtBeginSXCondFmt14", f:parsenoop },
0x047C: { n:"BrtEndSXCondFmt14", f:parsenoop },
0x047D: { n:"BrtBeginSXCondFmts14", f:parsenoop },
0x047E: { n:"BrtEndSXCondFmts14", f:parsenoop },
0x0480: { n:"BrtBeginSortCond14", f:parsenoop },
0x0481: { n:"BrtEndSortCond14", f:parsenoop },
0x0482: { n:"BrtEndDVals14", f:parsenoop },
0x0483: { n:"BrtEndIconSet14", f:parsenoop },
0x0484: { n:"BrtEndDatabar14", f:parsenoop },
0x0485: { n:"BrtBeginColorScale14", f:parsenoop },
0x0486: { n:"BrtEndColorScale14", f:parsenoop },
0x0487: { n:"BrtBeginSxrules14", f:parsenoop },
0x0488: { n:"BrtEndSxrules14", f:parsenoop },
0x0489: { n:"BrtBeginPRule14", f:parsenoop },
0x048A: { n:"BrtEndPRule14", f:parsenoop },
0x048B: { n:"BrtBeginPRFilters14", f:parsenoop },
0x048C: { n:"BrtEndPRFilters14", f:parsenoop },
0x048D: { n:"BrtBeginPRFilter14", f:parsenoop },
0x048E: { n:"BrtEndPRFilter14", f:parsenoop },
0x048F: { n:"BrtBeginPRFItem14", f:parsenoop },
0x0490: { n:"BrtEndPRFItem14", f:parsenoop },
0x0491: { n:"BrtBeginCellIgnoreECs14", f:parsenoop },
0x0492: { n:"BrtEndCellIgnoreECs14", f:parsenoop },
0x0493: { n:"BrtDxf14", f:parsenoop },
0x0494: { n:"BrtBeginDxF14s", f:parsenoop },
0x0495: { n:"BrtEndDxf14s", f:parsenoop },
0x0499: { n:"BrtFilter14", f:parsenoop },
0x049A: { n:"BrtBeginCustomFilters14", f:parsenoop },
0x049C: { n:"BrtCustomFilter14", f:parsenoop },
0x049D: { n:"BrtIconFilter14", f:parsenoop },
0x049E: { n:"BrtPivotCacheConnectionName", f:parsenoop },
0x0800: { n:"BrtBeginDecoupledPivotCacheIDs", f:parsenoop },
0x0801: { n:"BrtEndDecoupledPivotCacheIDs", f:parsenoop },
0x0802: { n:"BrtDecoupledPivotCacheID", f:parsenoop },
0x0803: { n:"BrtBeginPivotTableRefs", f:parsenoop },
0x0804: { n:"BrtEndPivotTableRefs", f:parsenoop },
0x0805: { n:"BrtPivotTableRef", f:parsenoop },
0x0806: { n:"BrtSlicerCacheBookPivotTables", f:parsenoop },
0x0807: { n:"BrtBeginSxvcells", f:parsenoop },
0x0808: { n:"BrtEndSxvcells", f:parsenoop },
0x0809: { n:"BrtBeginSxRow", f:parsenoop },
0x080A: { n:"BrtEndSxRow", f:parsenoop },
0x080C: { n:"BrtPcdCalcMem15", f:parsenoop },
0x0813: { n:"BrtQsi15", f:parsenoop },
0x0814: { n:"BrtBeginWebExtensions", f:parsenoop },
0x0815: { n:"BrtEndWebExtensions", f:parsenoop },
0x0816: { n:"BrtWebExtension", f:parsenoop },
0x0817: { n:"BrtAbsPath15", f:parsenoop },
0x0818: { n:"BrtBeginPivotTableUISettings", f:parsenoop },
0x0819: { n:"BrtEndPivotTableUISettings", f:parsenoop },
0x081B: { n:"BrtTableSlicerCacheIDs", f:parsenoop },
0x081C: { n:"BrtTableSlicerCacheID", f:parsenoop },
0x081D: { n:"BrtBeginTableSlicerCache", f:parsenoop },
0x081E: { n:"BrtEndTableSlicerCache", f:parsenoop },
0x081F: { n:"BrtSxFilter15", f:parsenoop },
0x0820: { n:"BrtBeginTimelineCachePivotCacheIDs", f:parsenoop },
0x0821: { n:"BrtEndTimelineCachePivotCacheIDs", f:parsenoop },
0x0822: { n:"BrtTimelineCachePivotCacheID", f:parsenoop },
0x0823: { n:"BrtBeginTimelineCacheIDs", f:parsenoop },
0x0824: { n:"BrtEndTimelineCacheIDs", f:parsenoop },
0x0825: { n:"BrtBeginTimelineCacheID", f:parsenoop },
0x0826: { n:"BrtEndTimelineCacheID", f:parsenoop },
0x0827: { n:"BrtBeginTimelinesEx", f:parsenoop },
0x0828: { n:"BrtEndTimelinesEx", f:parsenoop },
0x0829: { n:"BrtBeginTimelineEx", f:parsenoop },
0x082A: { n:"BrtEndTimelineEx", f:parsenoop },
0x082B: { n:"BrtWorkBookPr15", f:parsenoop },
0x082C: { n:"BrtPCDH15", f:parsenoop },
0x082D: { n:"BrtBeginTimelineStyle", f:parsenoop },
0x082E: { n:"BrtEndTimelineStyle", f:parsenoop },
0x082F: { n:"BrtTimelineStyleElement", f:parsenoop },
0x0830: { n:"BrtBeginTimelineStylesheetExt15", f:parsenoop },
0x0831: { n:"BrtEndTimelineStylesheetExt15", f:parsenoop },
0x0832: { n:"BrtBeginTimelineStyles", f:parsenoop },
0x0833: { n:"BrtEndTimelineStyles", f:parsenoop },
0x0834: { n:"BrtBeginTimelineStyleElements", f:parsenoop },
0x0835: { n:"BrtEndTimelineStyleElements", f:parsenoop },
0x0836: { n:"BrtDxf15", f:parsenoop },
0x0837: { n:"BrtBeginDxfs15", f:parsenoop },
0x0838: { n:"brtEndDxfs15", f:parsenoop },
0x0839: { n:"BrtSlicerCacheHideItemsWithNoData", f:parsenoop },
0x083A: { n:"BrtBeginItemUniqueNames", f:parsenoop },
0x083B: { n:"BrtEndItemUniqueNames", f:parsenoop },
0x083C: { n:"BrtItemUniqueName", f:parsenoop },
0x083D: { n:"BrtBeginExtConn15", f:parsenoop },
0x083E: { n:"BrtEndExtConn15", f:parsenoop },
0x083F: { n:"BrtBeginOledbPr15", f:parsenoop },
0x0840: { n:"BrtEndOledbPr15", f:parsenoop },
0x0841: { n:"BrtBeginDataFeedPr15", f:parsenoop },
0x0842: { n:"BrtEndDataFeedPr15", f:parsenoop },
0x0843: { n:"BrtTextPr15", f:parsenoop },
0x0844: { n:"BrtRangePr15", f:parsenoop },
0x0845: { n:"BrtDbCommand15", f:parsenoop },
0x0846: { n:"BrtBeginDbTables15", f:parsenoop },
0x0847: { n:"BrtEndDbTables15", f:parsenoop },
0x0848: { n:"BrtDbTable15", f:parsenoop },
0x0849: { n:"BrtBeginDataModel", f:parsenoop },
0x084A: { n:"BrtEndDataModel", f:parsenoop },
0x084B: { n:"BrtBeginModelTables", f:parsenoop },
0x084C: { n:"BrtEndModelTables", f:parsenoop },
0x084D: { n:"BrtModelTable", f:parsenoop },
0x084E: { n:"BrtBeginModelRelationships", f:parsenoop },
0x084F: { n:"BrtEndModelRelationships", f:parsenoop },
0x0850: { n:"BrtModelRelationship", f:parsenoop },
0x0851: { n:"BrtBeginECTxtWiz15", f:parsenoop },
0x0852: { n:"BrtEndECTxtWiz15", f:parsenoop },
0x0853: { n:"BrtBeginECTWFldInfoLst15", f:parsenoop },
0x0854: { n:"BrtEndECTWFldInfoLst15", f:parsenoop },
0x0855: { n:"BrtBeginECTWFldInfo15", f:parsenoop },
0x0856: { n:"BrtFieldListActiveItem", f:parsenoop },
0x0857: { n:"BrtPivotCacheIdVersion", f:parsenoop },
0x0858: { n:"BrtSXDI15", f:parsenoop },
0xFFFF: { n:"", f:parsenoop }
};

var evert_RE = evert_key(XLSBRecordEnum, 'n');

/* [MS-XLS] 2.3 Record Enumeration */
var XLSRecordEnum = {
0x0003: { n:"BIFF2NUM", f:parse_BIFF2NUM },
0x0004: { n:"BIFF2STR", f:parse_BIFF2STR },
0x0006: { n:"Formula", f:parse_Formula },
0x0009: { n:'BOF', f:parse_BOF },
0x000a: { n:'EOF', f:parse_EOF },
0x000c: { n:"CalcCount", f:parse_CalcCount },
0x000d: { n:"CalcMode", f:parse_CalcMode },
0x000e: { n:"CalcPrecision", f:parse_CalcPrecision },
0x000f: { n:"CalcRefMode", f:parse_CalcRefMode },
0x0010: { n:"CalcDelta", f:parse_CalcDelta },
0x0011: { n:"CalcIter", f:parse_CalcIter },
0x0012: { n:"Protect", f:parse_Protect },
0x0013: { n:"Password", f:parse_Password },
0x0014: { n:"Header", f:parse_Header },
0x0015: { n:"Footer", f:parse_Footer },
0x0017: { n:"ExternSheet", f:parse_ExternSheet },
0x0018: { n:"Lbl", f:parse_Lbl },
0x0019: { n:"WinProtect", f:parse_WinProtect },
0x001a: { n:"VerticalPageBreaks", f:parse_VerticalPageBreaks },
0x001b: { n:"HorizontalPageBreaks", f:parse_HorizontalPageBreaks },
0x001c: { n:"Note", f:parse_Note },
0x001d: { n:"Selection", f:parse_Selection },
0x0022: { n:"Date1904", f:parse_Date1904 },
0x0023: { n:"ExternName", f:parse_ExternName },
0x0026: { n:"LeftMargin", f:parse_LeftMargin },
0x0027: { n:"RightMargin", f:parse_RightMargin },
0x0028: { n:"TopMargin", f:parse_TopMargin },
0x0029: { n:"BottomMargin", f:parse_BottomMargin },
0x002a: { n:"PrintRowCol", f:parse_PrintRowCol },
0x002b: { n:"PrintGrid", f:parse_PrintGrid },
0x002f: { n:"FilePass", f:parse_FilePass },
0x0031: { n:"Font", f:parse_Font },
0x0033: { n:"PrintSize", f:parse_PrintSize },
0x003c: { n:"Continue", f:parse_Continue },
0x003d: { n:"Window1", f:parse_Window1 },
0x0040: { n:"Backup", f:parse_Backup },
0x0041: { n:"Pane", f:parse_Pane },
0x0042: { n:'CodePage', f:parse_CodePage },
0x004d: { n:"Pls", f:parse_Pls },
0x0050: { n:"DCon", f:parse_DCon },
0x0051: { n:"DConRef", f:parse_DConRef },
0x0052: { n:"DConName", f:parse_DConName },
0x0055: { n:"DefColWidth", f:parse_DefColWidth },
0x0059: { n:"XCT", f:parse_XCT },
0x005a: { n:"CRN", f:parse_CRN },
0x005b: { n:"FileSharing", f:parse_FileSharing },
0x005c: { n:'WriteAccess', f:parse_WriteAccess },
0x005d: { n:"Obj", f:parse_Obj },
0x005e: { n:"Uncalced", f:parse_Uncalced },
0x005f: { n:"CalcSaveRecalc", f:parse_CalcSaveRecalc },
0x0060: { n:"Template", f:parse_Template },
0x0061: { n:"Intl", f:parse_Intl },
0x0063: { n:"ObjProtect", f:parse_ObjProtect },
0x007d: { n:"ColInfo", f:parse_ColInfo },
0x0080: { n:"Guts", f:parse_Guts },
0x0081: { n:"WsBool", f:parse_WsBool },
0x0082: { n:"GridSet", f:parse_GridSet },
0x0083: { n:"HCenter", f:parse_HCenter },
0x0084: { n:"VCenter", f:parse_VCenter },
0x0085: { n:'BoundSheet8', f:parse_BoundSheet8 },
0x0086: { n:"WriteProtect", f:parse_WriteProtect },
0x008c: { n:"Country", f:parse_Country },
0x008d: { n:"HideObj", f:parse_HideObj },
0x0090: { n:"Sort", f:parse_Sort },
0x0092: { n:"Palette", f:parse_Palette },
0x0097: { n:"Sync", f:parse_Sync },
0x0098: { n:"LPr", f:parse_LPr },
0x0099: { n:"DxGCol", f:parse_DxGCol },
0x009a: { n:"FnGroupName", f:parse_FnGroupName },
0x009b: { n:"FilterMode", f:parse_FilterMode },
0x009c: { n:"BuiltInFnGroupCount", f:parse_BuiltInFnGroupCount },
0x009d: { n:"AutoFilterInfo", f:parse_AutoFilterInfo },
0x009e: { n:"AutoFilter", f:parse_AutoFilter },
0x00a0: { n:"Scl", f:parse_Scl },
0x00a1: { n:"Setup", f:parse_Setup },
0x00ae: { n:"ScenMan", f:parse_ScenMan },
0x00af: { n:"SCENARIO", f:parse_SCENARIO },
0x00b0: { n:"SxView", f:parse_SxView },
0x00b1: { n:"Sxvd", f:parse_Sxvd },
0x00b2: { n:"SXVI", f:parse_SXVI },
0x00b4: { n:"SxIvd", f:parse_SxIvd },
0x00b5: { n:"SXLI", f:parse_SXLI },
0x00b6: { n:"SXPI", f:parse_SXPI },
0x00b8: { n:"DocRoute", f:parse_DocRoute },
0x00b9: { n:"RecipName", f:parse_RecipName },
0x00bd: { n:"MulRk", f:parse_MulRk },
0x00be: { n:"MulBlank", f:parse_MulBlank },
0x00c1: { n:'Mms', f:parse_Mms },
0x00c5: { n:"SXDI", f:parse_SXDI },
0x00c6: { n:"SXDB", f:parse_SXDB },
0x00c7: { n:"SXFDB", f:parse_SXFDB },
0x00c8: { n:"SXDBB", f:parse_SXDBB },
0x00c9: { n:"SXNum", f:parse_SXNum },
0x00ca: { n:"SxBool", f:parse_SxBool },
0x00cb: { n:"SxErr", f:parse_SxErr },
0x00cc: { n:"SXInt", f:parse_SXInt },
0x00cd: { n:"SXString", f:parse_SXString },
0x00ce: { n:"SXDtr", f:parse_SXDtr },
0x00cf: { n:"SxNil", f:parse_SxNil },
0x00d0: { n:"SXTbl", f:parse_SXTbl },
0x00d1: { n:"SXTBRGIITM", f:parse_SXTBRGIITM },
0x00d2: { n:"SxTbpg", f:parse_SxTbpg },
0x00d3: { n:"ObProj", f:parse_ObProj },
0x00d5: { n:"SXStreamID", f:parse_SXStreamID },
0x00d7: { n:"DBCell", f:parse_DBCell },
0x00d8: { n:"SXRng", f:parse_SXRng },
0x00d9: { n:"SxIsxoper", f:parse_SxIsxoper },
0x00da: { n:"BookBool", f:parse_BookBool },
0x00dc: { n:"DbOrParamQry", f:parse_DbOrParamQry },
0x00dd: { n:"ScenarioProtect", f:parse_ScenarioProtect },
0x00de: { n:"OleObjectSize", f:parse_OleObjectSize },
0x00e0: { n:"XF", f:parse_XF },
0x00e1: { n:'InterfaceHdr', f:parse_InterfaceHdr },
0x00e2: { n:'InterfaceEnd', f:parse_InterfaceEnd },
0x00e3: { n:"SXVS", f:parse_SXVS },
0x00e5: { n:"MergeCells", f:parse_MergeCells },
0x00e9: { n:"BkHim", f:parse_BkHim },
0x00eb: { n:"MsoDrawingGroup", f:parse_MsoDrawingGroup },
0x00ec: { n:"MsoDrawing", f:parse_MsoDrawing },
0x00ed: { n:"MsoDrawingSelection", f:parse_MsoDrawingSelection },
0x00ef: { n:"PhoneticInfo", f:parse_PhoneticInfo },
0x00f0: { n:"SxRule", f:parse_SxRule },
0x00f1: { n:"SXEx", f:parse_SXEx },
0x00f2: { n:"SxFilt", f:parse_SxFilt },
0x00f4: { n:"SxDXF", f:parse_SxDXF },
0x00f5: { n:"SxItm", f:parse_SxItm },
0x00f6: { n:"SxName", f:parse_SxName },
0x00f7: { n:"SxSelect", f:parse_SxSelect },
0x00f8: { n:"SXPair", f:parse_SXPair },
0x00f9: { n:"SxFmla", f:parse_SxFmla },
0x00fb: { n:"SxFormat", f:parse_SxFormat },
0x00fc: { n:"SST", f:parse_SST },
0x00fd: { n:"LabelSst", f:parse_LabelSst },
0x00ff: { n:"ExtSST", f:parse_ExtSST },
0x0100: { n:"SXVDEx", f:parse_SXVDEx },
0x0103: { n:"SXFormula", f:parse_SXFormula },
0x0122: { n:"SXDBEx", f:parse_SXDBEx },
0x0137: { n:"RRDInsDel", f:parse_RRDInsDel },
0x0138: { n:"RRDHead", f:parse_RRDHead },
0x013b: { n:"RRDChgCell", f:parse_RRDChgCell },
0x013d: { n:"RRTabId", f:parse_RRTabId },
0x013e: { n:"RRDRenSheet", f:parse_RRDRenSheet },
0x013f: { n:"RRSort", f:parse_RRSort },
0x0140: { n:"RRDMove", f:parse_RRDMove },
0x014a: { n:"RRFormat", f:parse_RRFormat },
0x014b: { n:"RRAutoFmt", f:parse_RRAutoFmt },
0x014d: { n:"RRInsertSh", f:parse_RRInsertSh },
0x014e: { n:"RRDMoveBegin", f:parse_RRDMoveBegin },
0x014f: { n:"RRDMoveEnd", f:parse_RRDMoveEnd },
0x0150: { n:"RRDInsDelBegin", f:parse_RRDInsDelBegin },
0x0151: { n:"RRDInsDelEnd", f:parse_RRDInsDelEnd },
0x0152: { n:"RRDConflict", f:parse_RRDConflict },
0x0153: { n:"RRDDefName", f:parse_RRDDefName },
0x0154: { n:"RRDRstEtxp", f:parse_RRDRstEtxp },
0x015f: { n:"LRng", f:parse_LRng },
0x0160: { n:"UsesELFs", f:parse_UsesELFs },
0x0161: { n:"DSF", f:parse_DSF },
0x0191: { n:"CUsr", f:parse_CUsr },
0x0192: { n:"CbUsr", f:parse_CbUsr },
0x0193: { n:"UsrInfo", f:parse_UsrInfo },
0x0194: { n:"UsrExcl", f:parse_UsrExcl },
0x0195: { n:"FileLock", f:parse_FileLock },
0x0196: { n:"RRDInfo", f:parse_RRDInfo },
0x0197: { n:"BCUsrs", f:parse_BCUsrs },
0x0198: { n:"UsrChk", f:parse_UsrChk },
0x01a9: { n:"UserBView", f:parse_UserBView },
0x01aa: { n:"UserSViewBegin", f:parse_UserSViewBegin },
0x01ab: { n:"UserSViewEnd", f:parse_UserSViewEnd },
0x01ac: { n:"RRDUserView", f:parse_RRDUserView },
0x01ad: { n:"Qsi", f:parse_Qsi },
0x01ae: { n:"SupBook", f:parse_SupBook },
0x01af: { n:"Prot4Rev", f:parse_Prot4Rev },
0x01b0: { n:"CondFmt", f:parse_CondFmt },
0x01b1: { n:"CF", f:parse_CF },
0x01b2: { n:"DVal", f:parse_DVal },
0x01b5: { n:"DConBin", f:parse_DConBin },
0x01b6: { n:"TxO", f:parse_TxO },
0x01b7: { n:"RefreshAll", f:parse_RefreshAll },
0x01b8: { n:"HLink", f:parse_HLink },
0x01b9: { n:"Lel", f:parse_Lel },
0x01ba: { n:"CodeName", f:parse_XLSCodeName },
0x01bb: { n:"SXFDBType", f:parse_SXFDBType },
0x01bc: { n:"Prot4RevPass", f:parse_Prot4RevPass },
0x01bd: { n:"ObNoMacros", f:parse_ObNoMacros },
0x01be: { n:"Dv", f:parse_Dv },
0x01c0: { n:"Excel9File", f:parse_Excel9File },
0x01c1: { n:"RecalcId", f:parse_RecalcId, r:2},
0x01c2: { n:"EntExU2", f:parse_EntExU2 },
0x0200: { n:"Dimensions", f:parse_Dimensions },
0x0201: { n:"Blank", f:parse_Blank },
0x0203: { n:"Number", f:parse_Number },
0x0204: { n:"Label", f:parse_Label },
0x0205: { n:"BoolErr", f:parse_BoolErr },
0x0206: { n:"Formula", f:parse_Formula },
0x0207: { n:"String", f:parse_String },
0x0208: { n:'Row', f:parse_Row },
0x020b: { n:"Index", f:parse_Index },
0x0221: { n:"Array", f:parse_Array },
0x0225: { n:"DefaultRowHeight", f:parse_DefaultRowHeight },
0x0236: { n:"Table", f:parse_Table },
0x023e: { n:"Window2", f:parse_Window2 },
0x027e: { n:"RK", f:parse_RK },
0x0293: { n:"Style", f:parse_Style },
0x0406: { n:"Formula", f:parse_Formula },
0x0418: { n:"BigName", f:parse_BigName },
0x041e: { n:"Format", f:parse_Format },
0x043c: { n:"ContinueBigName", f:parse_ContinueBigName },
0x04bc: { n:"ShrFmla", f:parse_ShrFmla },
0x0800: { n:"HLinkTooltip", f:parse_HLinkTooltip },
0x0801: { n:"WebPub", f:parse_WebPub },
0x0802: { n:"QsiSXTag", f:parse_QsiSXTag },
0x0803: { n:"DBQueryExt", f:parse_DBQueryExt },
0x0804: { n:"ExtString", f:parse_ExtString },
0x0805: { n:"TxtQry", f:parse_TxtQry },
0x0806: { n:"Qsir", f:parse_Qsir },
0x0807: { n:"Qsif", f:parse_Qsif },
0x0808: { n:"RRDTQSIF", f:parse_RRDTQSIF },
0x0809: { n:'BOF', f:parse_BOF },
0x080a: { n:"OleDbConn", f:parse_OleDbConn },
0x080b: { n:"WOpt", f:parse_WOpt },
0x080c: { n:"SXViewEx", f:parse_SXViewEx },
0x080d: { n:"SXTH", f:parse_SXTH },
0x080e: { n:"SXPIEx", f:parse_SXPIEx },
0x080f: { n:"SXVDTEx", f:parse_SXVDTEx },
0x0810: { n:"SXViewEx9", f:parse_SXViewEx9 },
0x0812: { n:"ContinueFrt", f:parse_ContinueFrt },
0x0813: { n:"RealTimeData", f:parse_RealTimeData },
0x0850: { n:"ChartFrtInfo", f:parse_ChartFrtInfo },
0x0851: { n:"FrtWrapper", f:parse_FrtWrapper },
0x0852: { n:"StartBlock", f:parse_StartBlock },
0x0853: { n:"EndBlock", f:parse_EndBlock },
0x0854: { n:"StartObject", f:parse_StartObject },
0x0855: { n:"EndObject", f:parse_EndObject },
0x0856: { n:"CatLab", f:parse_CatLab },
0x0857: { n:"YMult", f:parse_YMult },
0x0858: { n:"SXViewLink", f:parse_SXViewLink },
0x0859: { n:"PivotChartBits", f:parse_PivotChartBits },
0x085a: { n:"FrtFontList", f:parse_FrtFontList },
0x0862: { n:"SheetExt", f:parse_SheetExt },
0x0863: { n:"BookExt", f:parse_BookExt, r:12},
0x0864: { n:"SXAddl", f:parse_SXAddl },
0x0865: { n:"CrErr", f:parse_CrErr },
0x0866: { n:"HFPicture", f:parse_HFPicture },
0x0867: { n:'FeatHdr', f:parse_FeatHdr },
0x0868: { n:"Feat", f:parse_Feat },
0x086a: { n:"DataLabExt", f:parse_DataLabExt },
0x086b: { n:"DataLabExtContents", f:parse_DataLabExtContents },
0x086c: { n:"CellWatch", f:parse_CellWatch },
0x0871: { n:"FeatHdr11", f:parse_FeatHdr11 },
0x0872: { n:"Feature11", f:parse_Feature11 },
0x0874: { n:"DropDownObjIds", f:parse_DropDownObjIds },
0x0875: { n:"ContinueFrt11", f:parse_ContinueFrt11 },
0x0876: { n:"DConn", f:parse_DConn },
0x0877: { n:"List12", f:parse_List12 },
0x0878: { n:"Feature12", f:parse_Feature12 },
0x0879: { n:"CondFmt12", f:parse_CondFmt12 },
0x087a: { n:"CF12", f:parse_CF12 },
0x087b: { n:"CFEx", f:parse_CFEx },
0x087c: { n:"XFCRC", f:parse_XFCRC, r:12 },
0x087d: { n:"XFExt", f:parse_XFExt, r:12 },
0x087e: { n:"AutoFilter12", f:parse_AutoFilter12 },
0x087f: { n:"ContinueFrt12", f:parse_ContinueFrt12 },
0x0884: { n:"MDTInfo", f:parse_MDTInfo },
0x0885: { n:"MDXStr", f:parse_MDXStr },
0x0886: { n:"MDXTuple", f:parse_MDXTuple },
0x0887: { n:"MDXSet", f:parse_MDXSet },
0x0888: { n:"MDXProp", f:parse_MDXProp },
0x0889: { n:"MDXKPI", f:parse_MDXKPI },
0x088a: { n:"MDB", f:parse_MDB },
0x088b: { n:"PLV", f:parse_PLV },
0x088c: { n:"Compat12", f:parse_Compat12, r:12 },
0x088d: { n:"DXF", f:parse_DXF },
0x088e: { n:"TableStyles", f:parse_TableStyles, r:12 },
0x088f: { n:"TableStyle", f:parse_TableStyle },
0x0890: { n:"TableStyleElement", f:parse_TableStyleElement },
0x0892: { n:"StyleExt", f:parse_StyleExt },
0x0893: { n:"NamePublish", f:parse_NamePublish },
0x0894: { n:"NameCmt", f:parse_NameCmt, r:12 },
0x0895: { n:"SortData", f:parse_SortData },
0x0896: { n:"Theme", f:parse_Theme, r:12 },
0x0897: { n:"GUIDTypeLib", f:parse_GUIDTypeLib },
0x0898: { n:"FnGrp12", f:parse_FnGrp12 },
0x0899: { n:"NameFnGrp12", f:parse_NameFnGrp12 },
0x089a: { n:"MTRSettings", f:parse_MTRSettings, r:12 },
0x089b: { n:"CompressPictures", f:parse_CompressPictures },
0x089c: { n:"HeaderFooter", f:parse_HeaderFooter },
0x089d: { n:"CrtLayout12", f:parse_CrtLayout12 },
0x089e: { n:"CrtMlFrt", f:parse_CrtMlFrt },
0x089f: { n:"CrtMlFrtContinue", f:parse_CrtMlFrtContinue },
0x08a3: { n:"ForceFullCalculation", f:parse_ForceFullCalculation },
0x08a4: { n:"ShapePropsStream", f:parse_ShapePropsStream },
0x08a5: { n:"TextPropsStream", f:parse_TextPropsStream },
0x08a6: { n:"RichTextStream", f:parse_RichTextStream },
0x08a7: { n:"CrtLayout12A", f:parse_CrtLayout12A },
0x1001: { n:"Units", f:parse_Units },
0x1002: { n:"Chart", f:parse_Chart },
0x1003: { n:"Series", f:parse_Series },
0x1006: { n:"DataFormat", f:parse_DataFormat },
0x1007: { n:"LineFormat", f:parse_LineFormat },
0x1009: { n:"MarkerFormat", f:parse_MarkerFormat },
0x100a: { n:"AreaFormat", f:parse_AreaFormat },
0x100b: { n:"PieFormat", f:parse_PieFormat },
0x100c: { n:"AttachedLabel", f:parse_AttachedLabel },
0x100d: { n:"SeriesText", f:parse_SeriesText },
0x1014: { n:"ChartFormat", f:parse_ChartFormat },
0x1015: { n:"Legend", f:parse_Legend },
0x1016: { n:"SeriesList", f:parse_SeriesList },
0x1017: { n:"Bar", f:parse_Bar },
0x1018: { n:"Line", f:parse_Line },
0x1019: { n:"Pie", f:parse_Pie },
0x101a: { n:"Area", f:parse_Area },
0x101b: { n:"Scatter", f:parse_Scatter },
0x101c: { n:"CrtLine", f:parse_CrtLine },
0x101d: { n:"Axis", f:parse_Axis },
0x101e: { n:"Tick", f:parse_Tick },
0x101f: { n:"ValueRange", f:parse_ValueRange },
0x1020: { n:"CatSerRange", f:parse_CatSerRange },
0x1021: { n:"AxisLine", f:parse_AxisLine },
0x1022: { n:"CrtLink", f:parse_CrtLink },
0x1024: { n:"DefaultText", f:parse_DefaultText },
0x1025: { n:"Text", f:parse_Text },
0x1026: { n:"FontX", f:parse_FontX },
0x1027: { n:"ObjectLink", f:parse_ObjectLink },
0x1032: { n:"Frame", f:parse_Frame },
0x1033: { n:"Begin", f:parse_Begin },
0x1034: { n:"End", f:parse_End },
0x1035: { n:"PlotArea", f:parse_PlotArea },
0x103a: { n:"Chart3d", f:parse_Chart3d },
0x103c: { n:"PicF", f:parse_PicF },
0x103d: { n:"DropBar", f:parse_DropBar },
0x103e: { n:"Radar", f:parse_Radar },
0x103f: { n:"Surf", f:parse_Surf },
0x1040: { n:"RadarArea", f:parse_RadarArea },
0x1041: { n:"AxisParent", f:parse_AxisParent },
0x1043: { n:"LegendException", f:parse_LegendException },
0x1044: { n:"ShtProps", f:parse_ShtProps },
0x1045: { n:"SerToCrt", f:parse_SerToCrt },
0x1046: { n:"AxesUsed", f:parse_AxesUsed },
0x1048: { n:"SBaseRef", f:parse_SBaseRef },
0x104a: { n:"SerParent", f:parse_SerParent },
0x104b: { n:"SerAuxTrend", f:parse_SerAuxTrend },
0x104e: { n:"IFmtRecord", f:parse_IFmtRecord },
0x104f: { n:"Pos", f:parse_Pos },
0x1050: { n:"AlRuns", f:parse_AlRuns },
0x1051: { n:"BRAI", f:parse_BRAI },
0x105b: { n:"SerAuxErrBar", f:parse_SerAuxErrBar },
0x105c: { n:"ClrtClient", f:parse_ClrtClient },
0x105d: { n:"SerFmt", f:parse_SerFmt },
0x105f: { n:"Chart3DBarShape", f:parse_Chart3DBarShape },
0x1060: { n:"Fbi", f:parse_Fbi },
0x1061: { n:"BopPop", f:parse_BopPop },
0x1062: { n:"AxcExt", f:parse_AxcExt },
0x1063: { n:"Dat", f:parse_Dat },
0x1064: { n:"PlotGrowth", f:parse_PlotGrowth },
0x1065: { n:"SIIndex", f:parse_SIIndex },
0x1066: { n:"GelFrame", f:parse_GelFrame },
0x1067: { n:"BopPopCustom", f:parse_BopPopCustom },
0x1068: { n:"Fbi2", f:parse_Fbi2 },

	/* These are specified in an older version of the spec */
0x0000: { n:"Dimensions", f:parse_Dimensions },
0x0002: { n:"BIFF2INT", f:parse_BIFF2INT },
0x0005: { n:"BoolErr", f:parse_BoolErr },
0x0007: { n:"String", f:parse_BIFF2STRING },
0x0008: { n:"BIFF2ROW", f:parsenoop },
0x000b: { n:"Index", f:parse_Index },
0x0016: { n:"ExternCount", f:parsenoop },
0x001e: { n:"BIFF2FORMAT", f:parse_BIFF2Format },
0x001f: { n:"BIFF2FMTCNT", f:parsenoop }, /* 16-bit cnt of BIFF2FORMAT records */
0x0020: { n:"BIFF2COLINFO", f:parsenoop },
0x0021: { n:"Array", f:parse_Array },
0x0025: { n:"DefaultRowHeight", f:parse_DefaultRowHeight },
0x0032: { n:"BIFF2FONTXTRA", f:parse_BIFF2FONTXTRA },
0x003e: { n:"BIFF2WINDOW2", f:parsenoop },
0x0045: { n:"BIFF2FONTCLR", f:parsenoop },
0x0056: { n:"BIFF4FMTCNT", f:parsenoop }, /* 16-bit cnt, similar to BIFF2 */
0x007e: { n:"RK", f:parsenoop }, /* Not necessarily same as 0x027e */
0x007f: { n:"ImData", f:parse_ImData },
0x0087: { n:"Addin", f:parsenoop },
0x0088: { n:"Edg", f:parsenoop },
0x0089: { n:"Pub", f:parsenoop },
0x0091: { n:"Sub", f:parsenoop },
0x0094: { n:"LHRecord", f:parsenoop },
0x0095: { n:"LHNGraph", f:parsenoop },
0x0096: { n:"Sound", f:parsenoop },
0x00a9: { n:"CoordList", f:parsenoop },
0x00ab: { n:"GCW", f:parsenoop },
0x00bc: { n:"ShrFmla", f:parsenoop }, /* Not necessarily same as 0x04bc */
0x00c2: { n:"AddMenu", f:parsenoop },
0x00c3: { n:"DelMenu", f:parsenoop },
0x00d6: { n:"RString", f:parse_RString },
0x00df: { n:"UDDesc", f:parsenoop },
0x00ea: { n:"TabIdConf", f:parsenoop },
0x0162: { n:"XL5Modify", f:parsenoop },
0x01a5: { n:"FileSharing2", f:parsenoop },
0x0209: { n:'BOF', f:parse_BOF },
0x0218: { n:"Lbl", f:parse_Lbl },
0x0223: { n:"ExternName", f:parse_ExternName },
0x0231: { n:"Font", f:parsenoop },
0x0409: { n:'BOF', f:parse_BOF },
0x086d: { n:"FeatInfo", f:parsenoop },
0x0873: { n:"FeatInfo11", f:parsenoop },
0x0881: { n:"SXAddl12", f:parsenoop },
0x08c0: { n:"AutoWebPub", f:parsenoop },
0x08c1: { n:"ListObj", f:parsenoop },
0x08c2: { n:"ListField", f:parsenoop },
0x08c3: { n:"ListDV", f:parsenoop },
0x08c4: { n:"ListCondFmt", f:parsenoop },
0x08c5: { n:"ListCF", f:parsenoop },
0x08c6: { n:"FMQry", f:parsenoop },
0x08c7: { n:"FMSQry", f:parsenoop },
0x08c8: { n:"PLV", f:parsenoop },
0x08c9: { n:"LnExt", f:parsenoop },
0x08ca: { n:"MkrExt", f:parsenoop },
0x08cb: { n:"CrtCoopt", f:parsenoop },

0x0043: { n:"BIFF2XF", f:parsenoop },
0x0243: { n:"BIFF3XF", f:parsenoop },
0x0443: { n:"BIFF4XF", f:parsenoop },

0x7262: {}
};


/* BIFF2-4 single-sheet workbooks */
function write_biff_rec(ba, t, payload, length) {
	var len = (length || (payload||[]).length);
	var o = ba.next(4 + len);
	o.write_shift(2, t);
	o.write_shift(2, len);
	if(len > 0 && is_buf(payload)) ba.push(payload);
}

function write_BOF(wb, o) {
	if(o.bookType != 'biff2') throw "unsupported BIFF version";
	var out = new_buf(4);
	out.write_shift(2, 0x0002); // "unused"
	out.write_shift(2, 0x0010); // Sheet
	return out;
}

function write_BIFF2Cell(out, r, c) {
	if(!out) out = new_buf(7);
	out.write_shift(2, r);
	out.write_shift(2, c);
	out.write_shift(1, 0);
	out.write_shift(1, 0);
	out.write_shift(1, 0);
	return out;
}

function write_BIFF2INT(r, c, val) {
	var out = new_buf(9);
	write_BIFF2Cell(out, r, c);
	out.write_shift(2, val);
	return out;
}

function write_BIFF2NUMBER(r, c, val) {
	var out = new_buf(15);
	write_BIFF2Cell(out, r, c);
	out.write_shift(8, val, 'f');
	return out;
}

function write_BIFF2BERR(r, c, val, t) {
	var out = new_buf(9);
	write_BIFF2Cell(out, r, c);
	if(t == 'e') { out.write_shift(1, val); out.write_shift(1, 1); }
	else { out.write_shift(1, val?1:0); out.write_shift(1, 0); }
	return out;
}

/* TODO: codepage, large strings */
function write_BIFF2LABEL(r, c, val) {
	var out = new_buf(8 + 2*val.length);
	write_BIFF2Cell(out, r, c);
	out.write_shift(1, val.length);
	out.write_shift(val.length, val, 'sbcs');
	return out.l < out.length ? out.slice(0, out.l) : out;
}

function write_ws_biff_cell(ba, cell, R, C, opts) {
	if(cell.v != null) switch(cell.t) {
		case 'd': case 'n':
			var v = cell.t == 'd' ? datenum(cell.v) : cell.v;
			if((v == (v|0)) && (v >= 0) && (v < 65536))
				write_biff_rec(ba, 0x0002, write_BIFF2INT(R, C, v));
			else
				write_biff_rec(ba, 0x0003, write_BIFF2NUMBER(R,C, v));
			return;
		case 'b': case 'e': write_biff_rec(ba, 0x0005, write_BIFF2BERR(R, C, cell.v, cell.t)); return;
		/* TODO: codepage, sst */
		case 's': case 'str':
			write_biff_rec(ba, 0x0004, write_BIFF2LABEL(R, C, cell.v));
			return;
	}
	write_biff_rec(ba, 0x0001, write_BIFF2Cell(null, R, C));
}

function write_biff_ws(ba, ws, idx, opts, wb) {
	var dense = Array.isArray(ws);
	var range = safe_decode_range(ws['!ref'] || "A1"), ref, rr = "", cols = [];
	for(var R = range.s.r; R <= range.e.r; ++R) {
		rr = encode_row(R);
		for(var C = range.s.c; C <= range.e.c; ++C) {
			if(R === range.s.r) cols[C] = encode_col(C);
			ref = cols[C] + rr;
			var cell = dense ? ws[R][C] : ws[ref];
			if(!cell) continue;
			/* write cell */
			write_ws_biff_cell(ba, cell, R, C, opts);
		}
	}
}

/* Based on test files */
function write_biff_buf(wb, opts) {
	var o = opts || {};
	if(DENSE != null && o.dense == null) o.dense = DENSE;
	var ba = buf_array();
	var idx = 0;
	for(var i=0;i<wb.SheetNames.length;++i) if(wb.SheetNames[i] == o.sheet) idx=i;
	if(idx == 0 && !!o.sheet && wb.SheetNames[0] != o.sheet) throw new Error("Sheet not found: " + o.sheet);
	write_biff_rec(ba, 0x0009, write_BOF(wb, o));
	/* ... */
	write_biff_ws(ba, wb.Sheets[wb.SheetNames[idx]], idx, o, wb);
	/* ... */
	write_biff_rec(ba, 0x000a);
	// TODO
	return ba.end();
}
/* note: browser DOM element cannot see mso- style attrs, must parse */
var HTML_ = (function() {
	function html_to_sheet(str, _opts) {
		var opts = _opts || {};
		if(DENSE != null && opts.dense == null) opts.dense = DENSE;
		var ws = opts.dense ? ([]) : ({});
		var i = str.indexOf("<table"), j = str.indexOf("</table");
		if(i == -1 || j == -1) throw new Error("Invalid HTML: missing <table> / </table> pair");
		var rows = str.slice(i, j).split(/(:?<tr[^>]*>)/);
		var R = -1, C = 0, RS = 0, CS = 0;
		var range = {s:{r:10000000, c:10000000},e:{r:0,c:0}};
		var merges = [], midx = 0;
		for(i = 0; i < rows.length; ++i) {
			var row = rows[i].trim();
			if(row.substr(0,3) == "<tr") { ++R; C = 0; continue; }
			if(row.substr(0,3) != "<td") continue;
			var cells = row.split("</td>");
			for(j = 0; j < cells.length; ++j) {
				var cell = cells[j].trim();
				if(cell.substr(0,3) != "<td") continue;
				var m = cell, cc = 0;
				/* TODO: parse styles etc */
				while(m.charAt(0) == "<" && (cc = m.indexOf(">")) > -1) m = m.slice(cc+1);
				while(m.indexOf(">") > -1) m = m.slice(0, m.lastIndexOf("<"));
				var tag = parsexmltag(cell.slice(0, cell.indexOf(">")));
				CS = tag.colspan ? +tag.colspan : 1;
				if((RS = +tag.rowspan)>0 || CS>1) merges.push({s:{r:R,c:C},e:{r:R + (RS||1) - 1, c:C + CS - 1}});
				/* TODO: generate stub cells */
				if(!m.length) { C += CS; continue; }
				m = unescapexml(m).replace(/[\r\n]/g,"");
				if(range.s.r > R) range.s.r = R;
				if(range.e.r < R) range.e.r = R;
				if(range.s.c > C) range.s.c = C;
				if(range.e.c < C) range.e.c = C;
				if(opts.dense) {
					if(!ws[R]) ws[R] = [];
					if(Number(m) == Number(m)) ws[R][C] = {t:'n', v:+m};
					else ws[R][C] = {t:'s', v:m};
				} else {
					var coord = encode_cell({r:R, c:C});
					/* TODO: value parsing */
					if(Number(m) == Number(m)) ws[coord] = {t:'n', v:+m};
					else ws[coord] = {t:'s', v:m};
				}
				C += CS;
			}
		}
		ws['!ref'] = encode_range(range);
		return ws;
	}
	function html_to_book(str, opts) {
		return sheet_to_workbook(html_to_sheet(str, opts), opts);
	}
	function make_html_row(ws, r, R, o) {
		var M = (ws['!merges'] ||[]);
		var oo = [];
		var nullcell = "<td" + (o.editable ? ' contenteditable="true"' : "" ) + "></td>";
		for(var C = r.s.c; C <= r.e.c; ++C) {
			var RS = 0, CS = 0;
			for(var j = 0; j < M.length; ++j) {
				if(M[j].s.r > R || M[j].s.c > C) continue;
				if(M[j].e.r < R || M[j].e.c < C) continue;
				if(M[j].s.r < R || M[j].s.c < C) { RS = -1; break; }
				RS = M[j].e.r - M[j].s.r + 1; CS = M[j].e.c - M[j].s.c + 1; break;
			}
			if(RS < 0) continue;
			var coord = encode_cell({r:R,c:C});
			var cell = o.dense ? (ws[R]||[])[C] : ws[coord];
			if(!cell || cell.v == null) { oo.push(nullcell); continue; }
			/* TODO: html entities */
			var w = cell.h || escapexml(cell.w || (format_cell(cell), cell.w) || "");
			var sp = {};
			if(RS > 1) sp.rowspan = RS;
			if(CS > 1) sp.colspan = CS;
			if(o.editable) sp.contenteditable = "true";
			oo.push(writextag('td', w, sp));
		}
		return "<tr>" + oo.join("") + "</tr>";
	}
	var _BEGIN = "<html><head><title>SheetJS Table Export</title></head><body><table>";
	var _END = "</table></body></html>";
	function sheet_to_html(ws, opts) {
		var o = opts || {};
		var out = [];
		var r = decode_range(ws['!ref']);
		o.dense = Array.isArray(ws);
		for(var R = r.s.r; R <= r.e.r; ++R) out.push(make_html_row(ws, r, R, o));
		var header = o.header != null ? o.header : _BEGIN;
		var footer = o.footer != null ? o.footer : _END;
		return header + out.join("") + footer ;
	}

	return {
		to_workbook: html_to_book,
		to_sheet: html_to_sheet,
		_row: make_html_row,
		BEGIN: _BEGIN,
		END: _END,
		from_sheet: sheet_to_html
	};
})();

function parse_dom_table(table, _opts) {
	var opts = _opts || {};
	if(DENSE != null) opts.dense = DENSE;
	var ws = opts.dense ? ([]) : ({});
	var rows = table.getElementsByTagName('tr');
	var range = {s:{r:0,c:0},e:{r:rows.length - 1,c:0}};
	var merges = [], midx = 0;
	var R = 0, _C = 0, C = 0, RS = 0, CS = 0;
	for(; R < rows.length; ++R) {
		var row = rows[R];
		var elts = row.children;
		for(_C = C = 0; _C < elts.length; ++_C) {
			var elt = elts[_C], v = elts[_C].innerText || elts[_C].textContent;
			for(midx = 0; midx < merges.length; ++midx) {
				var m = merges[midx];
				if(m.s.c == C && m.s.r <= R && R <= m.e.r) { C = m.e.c+1; midx = -1; }
			}
			/* TODO: figure out how to extract nonstandard mso- style */
			CS = +elt.getAttribute("colspan") || 1;
			if((RS = +elt.getAttribute("rowspan"))>0 || CS>1) merges.push({s:{r:R,c:C},e:{r:R + (RS||1) - 1, c:C + CS - 1}});
			var o = {t:'s', v:v};
			if(v != null && v.length) {
				if(!isNaN(Number(v))) o = {t:'n', v:Number(v)};
				else if(!isNaN(fuzzydate(v).getDate())) {
					o = ({t:'d', v:parseDate(v)});
					if(!opts.cellDates) o = ({t:'n', v:datenum(o.v)});
					o.z = opts.dateNF || SSF._table[14];
				}
			}
			if(opts.dense) { if(!ws[R]) ws[R] = []; ws[R][C] = o; }
			else ws[encode_cell({c:C, r:R})] = o;
			if(range.e.c < C) range.e.c = C;
			C += CS;
		}
	}
	ws['!merges'] = merges;
	ws['!ref'] = encode_range(range);
	return ws;
}

function table_to_book(table, opts) {
	return sheet_to_workbook(parse_dom_table(table, opts), opts);
}
/* OpenDocument */
var parse_content_xml = (function() {

	var parse_text_p = function(text, tag) {
		return unescapexml(text.replace(/<text:s\/>/g," ").replace(/<[^>]*>/g,""));
	};

	var number_formats = {
		/* ods name: [short ssf fmt, long ssf fmt] */
		day: ["d", "dd"],
		month: ["m", "mm"],
		year: ["y", "yy"],
		hours: ["h", "hh"],
		minutes: ["m", "mm"],
		seconds: ["s", "ss"],
		"am-pm": ["A/P", "AM/PM"],
		"day-of-week": ["ddd", "dddd"]
	};

	return function pcx(d, _opts) {
		var opts = _opts || {};
		if(DENSE != null && opts.dense == null) opts.dense = DENSE;
		var str = xlml_normalize(d);
		var state = [], tmp;
		var tag;
		var NFtag = {name:""}, NF = "", pidx = 0;
		var sheetag;
		var rowtag;
		var Sheets = {}, SheetNames = [];
		var ws = opts.dense ? ([]) : ({});
		var Rn, q;
		var ctag = {value:""};
		var textp = "", textpidx = 0, textptag;
		var R = -1, C = -1, range = {s: {r:1000000,c:10000000}, e: {r:0, c:0}};
		var number_format_map = {};
		var merges = [], mrange = {}, mR = 0, mC = 0;
		var arrayf = [];
		var comments = [], comment = {};
		var creator = "", creatoridx = 0;
		var rept = 1, isstub = false;
		var i = 0;
		xlmlregex.lastIndex = 0;
		str = str.replace(/<!--([^\u2603]*?)-->/mg,"").replace(/<!DOCTYPE[^\[]*\[[^\]]*\]>/gm,"");
		while((Rn = xlmlregex.exec(str))) switch((Rn[3]=Rn[3].replace(/_.*$/,""))) {

			case 'table': case '工作表': // 9.1.2 <table:table>
				if(Rn[1]==='/') {
					if(range.e.c >= range.s.c && range.e.r >= range.s.r) ws['!ref'] = encode_range(range);
					if(merges.length) ws['!merges'] = merges;
					sheetag.name = utf8read(sheetag['名称'] || sheetag.name);
					SheetNames.push(sheetag.name);
					Sheets[sheetag.name] = ws;
				}
				else if(Rn[0].charAt(Rn[0].length-2) !== '/') {
					sheetag = parsexmltag(Rn[0], false);
					R = C = -1;
					range.s.r = range.s.c = 10000000; range.e.r = range.e.c = 0;
					ws = opts.dense ? ([]) : ({}); merges = [];
				}
				break;

			case 'table-row': case '行': // 9.1.3 <table:table-row>
				if(Rn[1] === '/') break;
				rowtag = parsexmltag(Rn[0], false);
				if(rowtag['行号']) R = rowtag['行号'] - 1; else ++R;
				C = -1; break;
			case 'covered-table-cell': // 9.1.5 <table:covered-table-cell>
				++C;
				if(opts.sheetStubs) {
					if(opts.dense) { if(!ws[R]) ws[R] = []; ws[R][C] = {t:'z'}; }
					else ws[encode_cell({r:R,c:C})] = {t:'z'};
				}
				break; /* stub */
			case 'table-cell': case '数据':
				if(Rn[0].charAt(Rn[0].length-2) === '/') {
					ctag = parsexmltag(Rn[0], false);
					if(ctag['number-columns-repeated']) C+= parseInt(ctag['number-columns-repeated'], 10);
					else ++C;
				}
				else if(Rn[1]!=='/') {
					++C;
					rept = 1;
					if(C > range.e.c) range.e.c = C;
					if(R > range.e.r) range.e.r = R;
					if(C < range.s.c) range.s.c = C;
					if(R < range.s.r) range.s.r = R;
					ctag = parsexmltag(Rn[0], false);
					comments = []; comment = {};
					q = ({t:ctag['数据类型'] || ctag['value-type'], v:null});
					if(opts.cellFormula) {
						if(ctag.formula) ctag.formula = unescapexml(ctag.formula);
						if(ctag['number-matrix-columns-spanned'] && ctag['number-matrix-rows-spanned']) {
							mR = parseInt(ctag['number-matrix-rows-spanned'],10) || 0;
							mC = parseInt(ctag['number-matrix-columns-spanned'],10) || 0;
							mrange = {s: {r:R,c:C}, e:{r:R + mR-1,c:C + mC-1}};
							q.F = encode_range(mrange);
							arrayf.push([mrange, q.F]);
						}
						if(ctag.formula) q.f = ods_to_csf_formula(ctag.formula);
						else for(i = 0; i < arrayf.length; ++i)
							if(R >= arrayf[i][0].s.r && R <= arrayf[i][0].e.r)
								if(C >= arrayf[i][0].s.c && C <= arrayf[i][0].e.c)
									q.F = arrayf[i][1];
					}
					if(ctag['number-columns-spanned'] || ctag['number-rows-spanned']) {
						mR = parseInt(ctag['number-rows-spanned'],10) || 0;
						mC = parseInt(ctag['number-columns-spanned'],10) || 0;
						mrange = {s: {r:R,c:C}, e:{r:R + mR-1,c:C + mC-1}};
						merges.push(mrange);
					}

					/* 19.675.2 table:number-columns-repeated */
					if(ctag['number-columns-repeated']) rept = parseInt(ctag['number-columns-repeated'], 10);

					/* 19.385 office:value-type */
					switch(q.t) {
						case 'boolean': q.t = 'b'; q.v = parsexmlbool(ctag['boolean-value']); break;
						case 'float': q.t = 'n'; q.v = parseFloat(ctag.value); break;
						case 'percentage': q.t = 'n'; q.v = parseFloat(ctag.value); break;
						case 'currency': q.t = 'n'; q.v = parseFloat(ctag.value); break;
						case 'date': q.t = 'd'; q.v = parseDate(ctag['date-value']);
							if(!opts.cellDates) { q.t = 'n'; q.v = datenum(q.v); }
							q.z = 'm/d/yy'; break;
						case 'time': q.t = 'n'; q.v = parse_isodur(ctag['time-value'])/86400; break;
						case 'number': q.t = 'n'; q.v = parseFloat(ctag['数据数值']); break;
						default:
							if(q.t === 'string' || q.t === 'text' || !q.t) {
								q.t = 's';
								if(ctag['string-value'] != null) textp = unescapexml(ctag['string-value']);
							} else throw new Error('Unsupported value type ' + q.t);
					}
				} else {
					isstub = false;
					if(q.t === 's') {
						q.v = textp || '';
						isstub = textpidx == 0;
					}
					if(comments.length > 0) { q.c = comments; comments = []; }
					if(textp && opts.cellText !== false) q.w = textp;
					if(!isstub || opts.sheetStubs) {
						if(!(opts.sheetRows && opts.sheetRows < R)) {
							if(opts.dense) {
								if(!ws[R]) ws[R] = [];
								ws[R][C] = q;
								while(--rept > 0) ws[R][++C] = dup(q);
							} else {
								ws[encode_cell({r:R,c:C})] = q;
								while(--rept > 0) ws[encode_cell({r:R,c:++C})] = dup(q);
							}
							if(range.e.c <= C) range.e.c = C;
						}
					} else { C += rept; rept = 0; }
					q = {};
					textp = "";
				}
				break; // 9.1.4 <table:table-cell>

			/* pure state */
			case 'document': // TODO: <office:document> is the root for FODS
			case 'document-content': case '电子表格文档': // 3.1.3.2 <office:document-content>
			case 'spreadsheet': case '主体': // 3.7 <office:spreadsheet>
			case 'scripts': // 3.12 <office:scripts>
			case 'styles': // TODO <office:styles>
			case 'font-face-decls': // 3.14 <office:font-face-decls>
				if(Rn[1]==='/'){if((tmp=state.pop())[0]!==Rn[3]) throw "Bad state: "+tmp;}
				else if(Rn[0].charAt(Rn[0].length-2) !== '/') state.push([Rn[3], true]);
				break;

			case 'annotation': // 14.1 <office:annotation>
				if(Rn[1]==='/'){
					if((tmp=state.pop())[0]!==Rn[3]) throw "Bad state: "+tmp;
					comment.t = textp;
					comment.a = creator;
					comments.push(comment);
				}
				else if(Rn[0].charAt(Rn[0].length-2) !== '/') {state.push([Rn[3], false]);}
				creator = ""; creatoridx = 0;
				textp = ""; textpidx = 0;
				break;

			case 'creator': // 4.3.2.7 <dc:creator>
				if(Rn[1]==='/') { creator = str.slice(creatoridx,Rn.index); }
				else creatoridx = Rn.index + Rn[0].length;
				break;

			/* ignore state */
			case 'meta': case '元数据': // TODO: <office:meta> <uof:元数据> FODS/UOF
			case 'settings': // TODO: <office:settings>
			case 'config-item-set': // TODO: <office:config-item-set>
			case 'config-item-map-indexed': // TODO: <office:config-item-map-indexed>
			case 'config-item-map-entry': // TODO: <office:config-item-map-entry>
			case 'config-item-map-named': // TODO: <office:config-item-map-entry>
			case 'shapes': // 9.2.8 <table:shapes>
			case 'frame': // 10.4.2 <draw:frame>
			case 'text-box': // 10.4.3 <draw:text-box>
			case 'image': // 10.4.4 <draw:image>
			case 'data-pilot-tables': // 9.6.2 <table:data-pilot-tables>
			case 'list-style': // 16.30 <text:list-style>
			case 'form': // 13.13 <form:form>
			case 'dde-links': // 9.8 <table:dde-links>
			case 'event-listeners': // TODO
				if(Rn[1]==='/'){if((tmp=state.pop())[0]!==Rn[3]) throw "Bad state: "+tmp;}
				else if(Rn[0].charAt(Rn[0].length-2) !== '/') state.push([Rn[3], false]);
				textp = ""; textpidx = 0;
				break;

			case 'scientific-number': // TODO: <number:scientific-number>
				break;
			case 'currency-symbol': // TODO: <number:currency-symbol>
				break;
			case 'currency-style': // TODO: <number:currency-style>
				break;
			case 'number-style': // 16.27.2 <number:number-style>
			case 'percentage-style': // 16.27.9 <number:percentage-style>
			case 'date-style': // 16.27.10 <number:date-style>
			case 'time-style': // 16.27.18 <number:time-style>
				if(Rn[1]==='/'){
					number_format_map[NFtag.name] = NF;
					if((tmp=state.pop())[0]!==Rn[3]) throw "Bad state: "+tmp;
				} else if(Rn[0].charAt(Rn[0].length-2) !== '/') {
					NF = "";
					NFtag = parsexmltag(Rn[0], false);
					state.push([Rn[3], true]);
				} break;

			case 'script': break; // 3.13 <office:script>
			case 'libraries': break; // TODO: <ooo:libraries>
			case 'automatic-styles': break; // 3.15.3 <office:automatic-styles>
			case 'master-styles': break; // TODO: <office:automatic-styles>

			case 'default-style': // TODO: <style:default-style>
			case 'page-layout': break; // TODO: <style:page-layout>
			case 'style': break; // 16.2 <style:style>
			case 'map': break; // 16.3 <style:map>
			case 'font-face': break; // 16.21 <style:font-face>

			case 'paragraph-properties': break; // 17.6 <style:paragraph-properties>
			case 'table-properties': break; // 17.15 <style:table-properties>
			case 'table-column-properties': break; // 17.16 <style:table-column-properties>
			case 'table-row-properties': break; // 17.17 <style:table-row-properties>
			case 'table-cell-properties': break; // 17.18 <style:table-cell-properties>

			case 'number': // 16.27.3 <number:number>
				switch(state[state.length-1][0]) {
					case 'time-style':
					case 'date-style':
						tag = parsexmltag(Rn[0], false);
						NF += number_formats[Rn[3]][tag.style==='long'?1:0]; break;
				} break;

			case 'fraction': break; // TODO 16.27.6 <number:fraction>

			case 'day': // 16.27.11 <number:day>
			case 'month': // 16.27.12 <number:month>
			case 'year': // 16.27.13 <number:year>
			case 'era': // 16.27.14 <number:era>
			case 'day-of-week': // 16.27.15 <number:day-of-week>
			case 'week-of-year': // 16.27.16 <number:week-of-year>
			case 'quarter': // 16.27.17 <number:quarter>
			case 'hours': // 16.27.19 <number:hours>
			case 'minutes': // 16.27.20 <number:minutes>
			case 'seconds': // 16.27.21 <number:seconds>
			case 'am-pm': // 16.27.22 <number:am-pm>
				switch(state[state.length-1][0]) {
					case 'time-style':
					case 'date-style':
						tag = parsexmltag(Rn[0], false);
						NF += number_formats[Rn[3]][tag.style==='long'?1:0]; break;
				} break;

			case 'boolean-style': break; // 16.27.23 <number:boolean-style>
			case 'boolean': break; // 16.27.24 <number:boolean>
			case 'text-style': break; // 16.27.25 <number:text-style>
			case 'text': // 16.27.26 <number:text>
				if(Rn[0].slice(-2) === "/>") break;
				else if(Rn[1]==="/") switch(state[state.length-1][0]) {
					case 'number-style':
					case 'date-style':
					case 'time-style':
						NF += str.slice(pidx, Rn.index);
						break;
				}
				else pidx = Rn.index + Rn[0].length;
				break;
			case 'text-content': break; // 16.27.27 <number:text-content>
			case 'text-properties': break; // 16.27.27 <style:text-properties>

			case 'body': case '电子表格': break; // 3.3 16.9.6 19.726.3

			case 'forms': break; // 12.25.2 13.2
			case 'table-column': break; // 9.1.6 <table:table-column>

			case 'null-date': break; // 9.4.2 <table:null-date> TODO: date1904

			case 'graphic-properties': break; // 17.21 <style:graphic-properties>
			case 'calculation-settings': break; // 9.4.1 <table:calculation-settings>
			case 'named-expressions': break; // 9.4.11 <table:named-expressions>
			case 'named-range': break; // 9.4.12 <table:named-range>
			case 'named-expression': break; // 9.4.13 <table:named-expression>
			case 'sort': break; // 9.4.19 <table:sort>
			case 'sort-by': break; // 9.4.20 <table:sort-by>
			case 'sort-groups': break; // 9.4.22 <table:sort-groups>

			case 'span': break; // <text:span>
			case 'line-break': break; // 6.1.5 <text:line-break>
			case 'p': case '文本串':
				if(Rn[1]==='/') textp = (textp.length > 0 ? textp + "\n" : "") + parse_text_p(str.slice(textpidx,Rn.index), textptag);
				else { textptag = parsexmltag(Rn[0], false); textpidx = Rn.index + Rn[0].length; }
				break; // <text:p>

			case 'database-range': // 9.4.15 <table:database-range>
				if(Rn[1]==='/') break;
				try {
					var AutoFilter = ods_to_csf_range_3D(parsexmltag(Rn[0])['target-range-address']);
					Sheets[AutoFilter[0]]['!autofilter'] = { ref: AutoFilter[1] };
				} catch(e) {/* empty */}
				break;

			case 's': break; // <text:s>
			case 'date': break; // <*:date>

			case 'object': break; // 10.4.6.2 <draw:object>
			case 'title': case '标题': break; // <*:title> OR <uof:标题>
			case 'desc': break; // <*:desc>

			case 'table-source': break; // 9.2.6

			case 'iteration': break; // 9.4.3 <table:iteration>
			case 'content-validations': break; // 9.4.4 <table:
			case 'content-validation': break; // 9.4.5 <table:
			case 'error-message': break; // 9.4.7 <table:
			case 'database-ranges': break; // 9.4.14 <table:database-ranges>
			case 'filter': break; // 9.5.2 <table:filter>
			case 'filter-and': break; // 9.5.3 <table:filter-and>
			case 'filter-or': break; // 9.5.4 <table:filter-or>
			case 'filter-condition': break; // 9.5.5 <table:filter-condition>

			case 'list-level-style-bullet': break; // 16.31 <text:
			case 'list-level-style-number': break; // 16.32 <text:
			case 'list-level-properties': break; // 17.19 <style:

			/* 7.3 Document Fields */
			case 'sender-firstname': // 7.3.6.2
			case 'sender-lastname': // 7.3.6.3
			case 'sender-initials': // 7.3.6.4
			case 'sender-title': // 7.3.6.5
			case 'sender-position': // 7.3.6.6
			case 'sender-email': // 7.3.6.7
			case 'sender-phone-private': // 7.3.6.8
			case 'sender-fax': // 7.3.6.9
			case 'sender-company': // 7.3.6.10
			case 'sender-phone-work': // 7.3.6.11
			case 'sender-street': // 7.3.6.12
			case 'sender-city': // 7.3.6.13
			case 'sender-postal-code': // 7.3.6.14
			case 'sender-country': // 7.3.6.15
			case 'sender-state-or-province': // 7.3.6.16
			case 'author-name': // 7.3.7.1
			case 'author-initials': // 7.3.7.2
			case 'chapter': // 7.3.8
			case 'file-name': // 7.3.9
			case 'template-name': // 7.3.9
			case 'sheet-name': // 7.3.9
				break;

			case 'event-listener':
				break;
			/* TODO: FODS Properties */
			case 'initial-creator':
			case 'creation-date':
			case 'generator':
			case 'document-statistic':
			case 'user-defined':
				break;

			/* TODO: FODS Config */
			case 'config-item':
				break;

			/* TODO: style tokens */
			case 'page-number': break; // TODO <text:page-number>
			case 'page-count': break; // TODO <text:page-count>
			case 'time': break; // TODO <text:time>

			/* 9.6 Data Pilot Tables <table: */
			case 'data-pilot-table': // 9.6.3
			case 'source-cell-range': // 9.6.5
			case 'source-service': // 9.6.6
			case 'data-pilot-field': // 9.6.7
			case 'data-pilot-level': // 9.6.8
			case 'data-pilot-subtotals': // 9.6.9
			case 'data-pilot-subtotal': // 9.6.10
			case 'data-pilot-members': // 9.6.11
			case 'data-pilot-member': // 9.6.12
			case 'data-pilot-display-info': // 9.6.13
			case 'data-pilot-sort-info': // 9.6.14
			case 'data-pilot-layout-info': // 9.6.15
			case 'data-pilot-field-reference': // 9.6.16
			case 'data-pilot-groups': // 9.6.17
			case 'data-pilot-group': // 9.6.18
			case 'data-pilot-group-member': // 9.6.19
				break;

			/* 10.3 Drawing Shapes */
			case 'rect': // 10.3.2
				break;

			/* 14.6 DDE Connections */
			case 'dde-connection-decls': // 14.6.2 <text:
			case 'dde-connection-decl': // 14.6.3 <text:
			case 'dde-link': // 14.6.4 <table:
			case 'dde-source': // 14.6.5 <office:
				break;

			case 'properties': break; // 13.7 <form:properties>
			case 'property': break; // 13.8 <form:property>

			case 'a': break; // 6.1.8 hyperlink

			/* non-standard */
			case 'table-protection': break;
			case 'data-pilot-grand-total': break; // <table:
			default:
				if(Rn[2] === 'dc:') break; // TODO: properties
				if(Rn[2] === 'draw:') break; // TODO: drawing
				if(Rn[2] === 'style:') break; // TODO: styles
				if(Rn[2] === 'calcext:') break; // ignore undocumented extensions
				if(Rn[2] === 'loext:') break; // ignore undocumented extensions
				if(Rn[2] === 'uof:') break; // TODO: uof
				if(Rn[2] === '表:') break; // TODO: uof
				if(Rn[2] === '字:') break; // TODO: uof
				if(opts.WTF) throw new Error(Rn);
		}
		var out = {
			Sheets: Sheets,
			SheetNames: SheetNames
		};
		return out;
	};
})();

function parse_ods(zip, opts) {
	opts = opts || ({});
	var ods = !!safegetzipfile(zip, 'objectdata');
	if(ods) var manifest = parse_manifest(getzipdata(zip, 'META-INF/manifest.xml'), opts);
	var content = getzipstr(zip, 'content.xml');
	if(!content) throw new Error("Missing content.xml in " + (ods ? "ODS" : "UOF")+ " file");
	return parse_content_xml(ods ? content : utf8read(content), opts);
}
function parse_fods(data, opts) {
	return parse_content_xml(data, opts);
}

/* OpenDocument */
var write_styles_ods = (function() {
	var payload = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><office:document-styles xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0" xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:number="urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0" xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0" xmlns:of="urn:oasis:names:tc:opendocument:xmlns:of:1.2" office:version="1.2"></office:document-styles>';
	return function wso(wb, opts) {
		return payload;
	};
})();
var write_content_ods = (function() {
	var null_cell_xml = '          <table:table-cell />\n';
	var covered_cell_xml = '          <table:covered-table-cell/>\n';
	var write_ws = function(ws, wb, i, opts) {
		/* Section 9 Tables */
		var o = [];
		o.push('      <table:table table:name="' + escapexml(wb.SheetNames[i]) + '">\n');
		var R=0,C=0, range = decode_range(ws['!ref']);
		var marr = ws['!merges'] || [], mi = 0;
		var dense = Array.isArray(ws);
		for(R = 0; R < range.s.r; ++R) o.push('        <table:table-row></table:table-row>\n');
		for(; R <= range.e.r; ++R) {
			o.push('        <table:table-row>\n');
			for(C=0; C < range.s.c; ++C) o.push(null_cell_xml);
			for(; C <= range.e.c; ++C) {
				var skip = false, ct = {}, textp = "";
				for(mi = 0; mi != marr.length; ++mi) {
					if(marr[mi].s.c > C) continue;
					if(marr[mi].s.r > R) continue;
					if(marr[mi].e.c < C) continue;
					if(marr[mi].e.r < R) continue;
					if(marr[mi].s.c != C || marr[mi].s.r != R) skip = true;
					ct['table:number-columns-spanned'] = (marr[mi].e.c - marr[mi].s.c + 1);
					ct['table:number-rows-spanned'] =    (marr[mi].e.r - marr[mi].s.r + 1);
					break;
				}
				if(skip) { o.push(covered_cell_xml); continue; }
				var ref = encode_cell({r:R, c:C}), cell = dense ? (ws[R]||[])[C]: ws[ref];
				if(cell && cell.f) {
					ct['table:formula'] = escapexml(csf_to_ods_formula(cell.f));
					if(cell.F) {
						if(cell.F.substr(0, ref.length) == ref) {
							var _Fref = decode_range(cell.F);
							ct['table:number-matrix-columns-spanned'] = (_Fref.e.c - _Fref.s.c + 1);
							ct['table:number-matrix-rows-spanned'] =    (_Fref.e.r - _Fref.s.r + 1);
						}
					}
				}
				if(!cell) { o.push(null_cell_xml); continue; }
				switch(cell.t) {
					case 'b':
						textp = (cell.v ? 'TRUE' : 'FALSE');
						ct['office:value-type'] = "boolean";
						ct['office:boolean-value'] = (cell.v ? 'true' : 'false');
						break;
					case 'n':
						textp = (cell.w||String(cell.v||0));
						ct['office:value-type'] = "float";
						ct['office:value'] = (cell.v||0);
						break;
					case 's': case 'str':
						textp = escapexml(cell.v);
						ct['office:value-type'] = "string";
						break;
					case 'd':
						textp = (cell.w||(parseDate(cell.v).toISOString()));
						ct['office:value-type'] = "date";
						ct['office:date-value'] = (parseDate(cell.v).toISOString());
						ct['table:style-name'] = "ce1";
						break;
					//case 'e':
					default: o.push(null_cell_xml); continue;
				}
				o.push('          ' + writextag('table:table-cell', writextag('text:p', textp, {}), ct) + '\n');
			}
			o.push('        </table:table-row>\n');
		}
		o.push('      </table:table>\n');
		return o.join("");
	};

	var write_automatic_styles_ods = function(o) {
		o.push(' <office:automatic-styles>\n');
		o.push('  <number:date-style style:name="N37" number:automatic-order="true">\n');
		o.push('   <number:month number:style="long"/>\n');
		o.push('   <number:text>/</number:text>\n');
		o.push('   <number:day number:style="long"/>\n');
		o.push('   <number:text>/</number:text>\n');
		o.push('   <number:year/>\n');
		o.push('  </number:date-style>\n');
		o.push('  <style:style style:name="ce1" style:family="table-cell" style:parent-style-name="Default" style:data-style-name="N37"/>\n');
		o.push(' </office:automatic-styles>\n');
	};

	return function wcx(wb, opts) {
		var o = [XML_HEADER];
		/* 3.1.3.2 */
		var attr = wxt_helper({
			'xmlns:office':       "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
			'xmlns:table':        "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
			'xmlns:style':        "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
			'xmlns:text':         "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
			'xmlns:draw':         "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
			'xmlns:fo':           "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
			'xmlns:xlink':        "http://www.w3.org/1999/xlink",
			'xmlns:dc':           "http://purl.org/dc/elements/1.1/",
			'xmlns:meta':         "urn:oasis:names:tc:opendocument:xmlns:meta:1.0",
			'xmlns:number':       "urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0",
			'xmlns:presentation': "urn:oasis:names:tc:opendocument:xmlns:presentation:1.0",
			'xmlns:svg':          "urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0",
			'xmlns:chart':        "urn:oasis:names:tc:opendocument:xmlns:chart:1.0",
			'xmlns:dr3d':         "urn:oasis:names:tc:opendocument:xmlns:dr3d:1.0",
			'xmlns:math':         "http://www.w3.org/1998/Math/MathML",
			'xmlns:form':         "urn:oasis:names:tc:opendocument:xmlns:form:1.0",
			'xmlns:script':       "urn:oasis:names:tc:opendocument:xmlns:script:1.0",
			'xmlns:ooo':          "http://openoffice.org/2004/office",
			'xmlns:ooow':         "http://openoffice.org/2004/writer",
			'xmlns:oooc':         "http://openoffice.org/2004/calc",
			'xmlns:dom':          "http://www.w3.org/2001/xml-events",
			'xmlns:xforms':       "http://www.w3.org/2002/xforms",
			'xmlns:xsd':          "http://www.w3.org/2001/XMLSchema",
			'xmlns:xsi':          "http://www.w3.org/2001/XMLSchema-instance",
			'xmlns:sheet':        "urn:oasis:names:tc:opendocument:sh33tjs:1.0",
			'xmlns:rpt':          "http://openoffice.org/2005/report",
			'xmlns:of':           "urn:oasis:names:tc:opendocument:xmlns:of:1.2",
			'xmlns:xhtml':        "http://www.w3.org/1999/xhtml",
			'xmlns:grddl':        "http://www.w3.org/2003/g/data-view#",
			'xmlns:tableooo':     "http://openoffice.org/2009/table",
			'xmlns:drawooo':      "http://openoffice.org/2010/draw",
			'xmlns:calcext':      "urn:org:documentfoundation:names:experimental:calc:xmlns:calcext:1.0",
			'xmlns:loext':        "urn:org:documentfoundation:names:experimental:office:xmlns:loext:1.0",
			'xmlns:field':        "urn:openoffice:names:experimental:ooo-ms-interop:xmlns:field:1.0",
			'xmlns:formx':        "urn:openoffice:names:experimental:ooxml-odf-interop:xmlns:form:1.0",
			'xmlns:css3t':        "http://www.w3.org/TR/css3-text/",
			'office:version':     "1.2"
		});

		var fods = wxt_helper({
			'xmlns:config':"urn:oasis:names:tc:opendocument:xmlns:config:1.0",
			'office:mimetype':"application/vnd.oasis.opendocument.spreadsheet"
		});

		if(opts.bookType == "fods") o.push('<office:document' + attr + fods + '>\n');
		else o.push('<office:document-content' + attr  + '>\n');
		write_automatic_styles_ods(o);
		o.push('  <office:body>\n');
		o.push('    <office:spreadsheet>\n');
		for(var i = 0; i != wb.SheetNames.length; ++i) o.push(write_ws(wb.Sheets[wb.SheetNames[i]], wb, i, opts));
		o.push('    </office:spreadsheet>\n');
		o.push('  </office:body>\n');
		if(opts.bookType == "fods") o.push('</office:document>');
		else o.push('</office:document-content>');
		return o.join("");
	};
})();

function write_ods(wb, opts) {
	if(opts.bookType == "fods") return write_content_ods(wb, opts);

var zip = new jszip();
	var f = "";

	var manifest = [];
	var rdf = [];

	/* 3:3.3 and 2:2.2.4 */
	f = "mimetype";
	zip.file(f, "application/vnd.oasis.opendocument.spreadsheet");

	/* Part 1 Section 2.2 Documents */
	f = "content.xml";
	zip.file(f, write_content_ods(wb, opts));
	manifest.push([f, "text/xml"]);
	rdf.push([f, "ContentFile"]);

	/* TODO: these are hard-coded styles to satiate excel */
	f = "styles.xml";
	zip.file(f, write_styles_ods(wb, opts));
	manifest.push([f, "text/xml"]);
	rdf.push([f, "StylesFile"]);

	/* Part 3 Section 6 Metadata Manifest File */
	f = "manifest.rdf";
	zip.file(f, write_rdf(rdf, opts));
	manifest.push([f, "application/rdf+xml"]);

	/* TODO: this is hard-coded to satiate excel */
	f = "meta.xml";
	zip.file(f, write_meta_ods(wb, opts));
	manifest.push([f, "text/xml"]);
	rdf.push([f, "MetadataFile"]);

	/* Part 3 Section 4 Manifest File */
	f = "META-INF/manifest.xml";
	zip.file(f, write_manifest(manifest, opts));

	return zip;
}

/* actual implementation elsewhere, wrappers are for read/write */
function write_obj_str(factory) {
	return function write_str(wb, o) {
		var idx = 0;
		for(var i=0;i<wb.SheetNames.length;++i) if(wb.SheetNames[i] == o.sheet) idx=i;
		if(idx == 0 && !!o.sheet && wb.SheetNames[0] != o.sheet) throw new Error("Sheet not found: " + o.sheet);
		return factory.from_sheet(wb.Sheets[wb.SheetNames[idx]], o);
	};
}

var write_htm_str = write_obj_str(HTML_);
var write_csv_str = write_obj_str({from_sheet:sheet_to_csv});
var write_slk_str = write_obj_str(SYLK);
var write_dif_str = write_obj_str(DIF);
var write_prn_str = write_obj_str(PRN);
var write_txt_str = write_obj_str({from_sheet:sheet_to_txt});
function fix_opts_func(defaults) {
	return function fix_opts(opts) {
		for(var i = 0; i != defaults.length; ++i) {
			var d = defaults[i];
			if(opts[d[0]] === undefined) opts[d[0]] = d[1];
			if(d[2] === 'n') opts[d[0]] = Number(opts[d[0]]);
		}
	};
}

var fix_read_opts = fix_opts_func([
	['cellNF', false], /* emit cell number format string as .z */
	['cellHTML', true], /* emit html string as .h */
	['cellFormula', true], /* emit formulae as .f */
	['cellStyles', false], /* emits style/theme as .s */
	['cellText', true], /* emit formatted text as .w */
	['cellDates', false], /* emit date cells with type `d` */

	['sheetStubs', false], /* emit empty cells */
	['sheetRows', 0, 'n'], /* read n rows (0 = read all rows) */

	['bookDeps', false], /* parse calculation chains */
	['bookSheets', false], /* only try to get sheet names (no Sheets) */
	['bookProps', false], /* only try to get properties (no Sheets) */
	['bookFiles', false], /* include raw file structure (keys, files, cfb) */
	['bookVBA', false], /* include vba raw data (vbaraw) */

	['password',''], /* password */
	['WTF', false] /* WTF mode (throws errors) */
]);


var fix_write_opts = fix_opts_func([
	['cellDates', false], /* write date cells with type `d` */

	['bookSST', false], /* Generate Shared String Table */

	['bookType', 'xlsx'], /* Type of workbook (xlsx/m/b) */

	['compression', false], /* Use file compression */

	['WTF', false] /* WTF mode (throws errors) */
]);
function get_sheet_type(n) {
	if(RELS.WS.indexOf(n) > -1) return "sheet";
	if(RELS.CS && n == RELS.CS) return "chart";
	if(RELS.DS && n == RELS.DS) return "dialog";
	if(RELS.MS && n == RELS.MS) return "macro";
	if(!n || !n.length) return "sheet";
	return n;
}
function safe_parse_wbrels(wbrels, sheets) {
	if(!wbrels) return 0;
	try {
		wbrels = sheets.map(function pwbr(w) { if(!w.id) w.id = w.strRelID; return [w.name, wbrels['!id'][w.id].Target, get_sheet_type(wbrels['!id'][w.id].Type)]; });
	} catch(e) { return null; }
	return !wbrels || wbrels.length === 0 ? null : wbrels;
}

function safe_parse_sheet(zip, path, relsPath, sheet, sheetRels, sheets, stype, opts, wb, themes, styles) {
	try {
		sheetRels[sheet]=parse_rels(getzipstr(zip, relsPath, true), path);
		var data = getzipdata(zip, path);
		switch(stype) {
			case 'sheet': sheets[sheet]=parse_ws(data, path, opts,sheetRels[sheet], wb, themes, styles); break;
			case 'chart':
				var cs = parse_cs(data, path, opts,sheetRels[sheet], wb, themes, styles);
				sheets[sheet] = cs;
				if(!cs || !cs['!chart']) break;
				var dfile = resolve_path(cs['!chart'].Target, path);
				var drelsp = get_rels_path(dfile);
				var draw = parse_drawing(getzipstr(zip, dfile, true), parse_rels(getzipstr(zip,drelsp,true), dfile));
				var chartp = resolve_path(draw, dfile);
				var crelsp = get_rels_path(chartp);
				cs = parse_chart(getzipstr(zip, chartp, true), chartp, opts, parse_rels(getzipstr(zip, crelsp,true), chartp), wb, cs);
				break;
			case 'macro': sheets[sheet]=parse_ms(data, path, opts,sheetRels[sheet], wb, themes, styles); break;
			case 'dialog': sheets[sheet]=parse_ds(data, path, opts,sheetRels[sheet], wb, themes, styles); break;
		}
	} catch(e) { if(opts.WTF) throw e; }
}

var nodirs = function nodirs(x){return x.slice(-1) != '/';};
function parse_zip(zip, opts) {
	make_ssf(SSF);
	opts = opts || {};
	fix_read_opts(opts);
	reset_cp();

	/* OpenDocument Part 3 Section 2.2.1 OpenDocument Package */
	if(safegetzipfile(zip, 'META-INF/manifest.xml')) return parse_ods(zip, opts);
	/* UOC */
	if(safegetzipfile(zip, 'objectdata.xml')) return parse_ods(zip, opts);

	var entries = keys(zip.files).filter(nodirs).sort();
	var dir = parse_ct((getzipstr(zip, '[Content_Types].xml')), opts);
	var xlsb = false;
	var sheets, binname;
	if(dir.workbooks.length === 0) {
		binname = "xl/workbook.xml";
		if(getzipdata(zip,binname, true)) dir.workbooks.push(binname);
	}
	if(dir.workbooks.length === 0) {
		binname = "xl/workbook.bin";
		if(!getzipfile(zip,binname,true)) throw new Error("Could not find workbook");
		dir.workbooks.push(binname);
		xlsb = true;
	}
	if(dir.workbooks[0].slice(-3) == "bin") xlsb = true;
	if(xlsb) set_cp(1200);

	var themes = ({});
	var styles = ({});
	if(!opts.bookSheets && !opts.bookProps) {
		strs = [];
		if(dir.sst) strs=parse_sst(getzipdata(zip, dir.sst.replace(/^\//,'')), dir.sst, opts);

		if(opts.cellStyles && dir.themes.length) themes = parse_theme(getzipstr(zip, dir.themes[0].replace(/^\//,''), true)||"",dir.themes[0], opts);

		if(dir.style) styles = parse_sty(getzipdata(zip, dir.style.replace(/^\//,'')),dir.style, themes, opts);
	}

	var wb = parse_wb(getzipdata(zip, dir.workbooks[0].replace(/^\//,'')), dir.workbooks[0], opts);

	var props = {}, propdata = "";

	if(dir.coreprops.length !== 0) {
		propdata = getzipstr(zip, dir.coreprops[0].replace(/^\//,''), true);
		if(propdata) props = parse_core_props(propdata);
		if(dir.extprops.length !== 0) {
			propdata = getzipstr(zip, dir.extprops[0].replace(/^\//,''), true);
			if(propdata) parse_ext_props(propdata, props);
		}
	}

	var custprops = {};
	if(!opts.bookSheets || opts.bookProps) {
		if (dir.custprops.length !== 0) {
			propdata = getzipstr(zip, dir.custprops[0].replace(/^\//,''), true);
			if(propdata) custprops = parse_cust_props(propdata, opts);
		}
	}

	var out = ({});
	if(opts.bookSheets || opts.bookProps) {
		if(wb.Sheets) sheets = wb.Sheets.map(function pluck(x){ return x.name; });
		else if(props.Worksheets && props.SheetNames.length > 0) sheets=props.SheetNames;
		if(opts.bookProps) { out.Props = props; out.Custprops = custprops; }
		if(opts.bookSheets && typeof sheets !== 'undefined') out.SheetNames = sheets;
		if(opts.bookSheets ? out.SheetNames : opts.bookProps) return out;
	}
	sheets = {};

	var deps = {};
	if(opts.bookDeps && dir.calcchain) deps=parse_cc(getzipdata(zip, dir.calcchain.replace(/^\//,'')),dir.calcchain,opts);

	var i=0;
	var sheetRels = ({});
	var path, relsPath;

	{
		var wbsheets = wb.Sheets;
		props.Worksheets = wbsheets.length;
		props.SheetNames = [];
		for(var j = 0; j != wbsheets.length; ++j) {
			props.SheetNames[j] = wbsheets[j].name;
		}
	}

	var wbext = xlsb ? "bin" : "xml";
	var wbrelsfile = 'xl/_rels/workbook.' + wbext + '.rels';
	var wbrels = parse_rels(getzipstr(zip, wbrelsfile, true), wbrelsfile);
	if(wbrels) wbrels = safe_parse_wbrels(wbrels, wb.Sheets);
	/* Numbers iOS hack */
	var nmode = (getzipdata(zip,"xl/worksheets/sheet.xml",true))?1:0;
	for(i = 0; i != props.Worksheets; ++i) {
		var stype = "sheet";
		if(wbrels && wbrels[i]) {
			path = 'xl/' + (wbrels[i][1]).replace(/[\/]?xl\//, "");
			stype = wbrels[i][2];
		} else {
			path = 'xl/worksheets/sheet'+(i+1-nmode)+"." + wbext;
			path = path.replace(/sheet0\./,"sheet.");
		}
		relsPath = path.replace(/^(.*)(\/)([^\/]*)$/, "$1/_rels/$3.rels");
		safe_parse_sheet(zip, path, relsPath, props.SheetNames[i], sheetRels, sheets, stype, opts, wb, themes, styles);
	}

	if(dir.comments) parse_comments(zip, dir.comments, sheets, sheetRels, opts);

	out = ({
		Directory: dir,
		Workbook: wb,
		Props: props,
		Custprops: custprops,
		Deps: deps,
		Sheets: sheets,
		SheetNames: props.SheetNames,
		Strings: strs,
		Styles: styles,
		Themes: themes,
		SSF: SSF.get_table()
	});
	if(opts.bookFiles) {
		out.keys = entries;
		out.files = zip.files;
	}
	if(opts.bookVBA) {
		if(dir.vba.length > 0) out.vbaraw = getzipdata(zip,dir.vba[0].replace(/^\//,''),true);
		else if(dir.defaults && dir.defaults.bin === 'application/vnd.ms-office.vbaProject') out.vbaraw = getzipdata(zip,'xl/vbaProject.bin',true);
	}
	return out;
}

/* references to [MS-OFFCRYPTO] */
function parse_xlsxcfb(cfb, opts) {
	var f = 'Version';
	var data = cfb.find(f);
	if(!data) throw new Error("ECMA-376 Encrypted file missing " + f);
	var version = parse_DataSpaceVersionInfo(data.content);

	/* 2.3.4.1 */
	f = 'DataSpaceMap';
	data = cfb.find(f);
	if(!data) throw new Error("ECMA-376 Encrypted file missing " + f);
	var dsm = parse_DataSpaceMap(data.content);
	if(dsm.length != 1 || dsm[0].comps.length != 1 || dsm[0].comps[0].t != 0 || dsm[0].name != "StrongEncryptionDataSpace" || dsm[0].comps[0].v != "EncryptedPackage")
		throw new Error("ECMA-376 Encrypted file bad " + f);

	f = 'StrongEncryptionDataSpace';
	data = cfb.find(f);
	if(!data) throw new Error("ECMA-376 Encrypted file missing " + f);
	var seds = parse_DataSpaceDefinition(data.content);
	if(seds.length != 1 || seds[0] != "StrongEncryptionTransform")
		throw new Error("ECMA-376 Encrypted file bad " + f);

	/* 2.3.4.3 */
	f = '!Primary';
	data = cfb.find(f);
	if(!data) throw new Error("ECMA-376 Encrypted file missing " + f);
	var hdr = parse_Primary(data.content);

	f = 'EncryptionInfo';
	data = cfb.find(f);
	if(!data) throw new Error("ECMA-376 Encrypted file missing " + f);
	var einfo = parse_EncryptionInfo(data.content);

	throw new Error("File is password-protected");
}

function write_zip(wb, opts) {
	_shapeid = 1024;
	if(opts.bookType == "ods") return write_ods(wb, opts);
	if(wb && !wb.SSF) {
		wb.SSF = SSF.get_table();
	}
	if(wb && wb.SSF) {
		// $FlowIgnore
		make_ssf(SSF); SSF.load_table(wb.SSF);
		// $FlowIgnore
		opts.revssf = evert_num(wb.SSF); opts.revssf[wb.SSF[65535]] = 0;
		opts.ssf = wb.SSF;
	}
	opts.rels = {}; opts.wbrels = {};
	opts.Strings = []; opts.Strings.Count = 0; opts.Strings.Unique = 0;
	var wbext = opts.bookType == "xlsb" ? "bin" : "xml";
	var vbafmt = opts.bookType == "xlsb" || opts.bookType == "xlsm";
	var ct = ({
		workbooks:[], sheets:[], charts:[], dialogs:[], macros:[],
		rels:[], strs:[], comments:[],
		coreprops:[], extprops:[], custprops:[], themes:[], styles:[],
		calcchains:[], vba: [], drawings: [],
		TODO:[], xmlns: "" });
	fix_write_opts(opts = opts || {});
var zip = new jszip();
	var f = "", rId = 0;

	opts.cellXfs = [];
	get_cell_style(opts.cellXfs, {}, {revssf:{"General":0}});

	if(!wb.Props) wb.Props = {};

	f = "docProps/core.xml";
	zip.file(f, write_core_props(wb.Props, opts));
	ct.coreprops.push(f);
	add_rels(opts.rels, 2, f, RELS.CORE_PROPS);

f = "docProps/app.xml";
	if(wb.Props && wb.Props.SheetNames){/* empty */}
	else if(!wb.Workbook || !wb.Workbook.Sheets) wb.Props.SheetNames = wb.SheetNames;
	// $FlowIgnore
	else wb.Props.SheetNames = wb.SheetNames.map(function(x,i) { return [(wb.Workbook.Sheets[i]||{}).Hidden != 2, x];}).filter(function(x) { return x[0]; }).map(function(x) { return x[1]; });
	wb.Props.Worksheets = wb.Props.SheetNames.length;
	zip.file(f, write_ext_props(wb.Props, opts));
	ct.extprops.push(f);
	add_rels(opts.rels, 3, f, RELS.EXT_PROPS);

	if(wb.Custprops !== wb.Props && keys(wb.Custprops||{}).length > 0) {
		f = "docProps/custom.xml";
		zip.file(f, write_cust_props(wb.Custprops, opts));
		ct.custprops.push(f);
		add_rels(opts.rels, 4, f, RELS.CUST_PROPS);
	}

	f = "xl/workbook." + wbext;
	zip.file(f, write_wb(wb, f, opts));
	ct.workbooks.push(f);
	add_rels(opts.rels, 1, f, RELS.WB);

	for(rId=1;rId <= wb.SheetNames.length; ++rId) {
		var wsrels = {'!id':{}};
		var ws = wb.Sheets[wb.SheetNames[rId-1]];
		var _type = (ws || {})["!type"] || "sheet";
		switch(_type) {
		case "chart": /*
			f = "xl/chartsheets/sheet" + rId + "." + wbext;
			zip.file(f, write_cs(rId-1, f, opts, wb, wsrels));
			ct.charts.push(f);
			add_rels(wsrels, -1, "chartsheets/sheet" + rId + "." + wbext, RELS.CS);
			break; */
			/* falls through */
		default:
			f = "xl/worksheets/sheet" + rId + "." + wbext;
			zip.file(f, write_ws(rId-1, f, opts, wb, wsrels));
			ct.sheets.push(f);
			add_rels(opts.wbrels, -1, "worksheets/sheet" + rId + "." + wbext, RELS.WS[0]);
		}

		if(ws) {
			var comments = ws['!comments'];
			if(comments && comments.length > 0) {
				var cf = "xl/comments" + rId + "." + wbext;
				zip.file(cf, write_cmnt(comments, cf, opts));
				ct.comments.push(cf);
				add_rels(wsrels, -1, "../comments" + rId + "." + wbext, RELS.CMNT);
			}
			if(ws['!legacy']) {
				zip.file("xl/drawings/vmlDrawing" + (rId) + ".vml", write_comments_vml(rId, ws['!comments']));
			}
			delete ws['!comments'];
			delete ws['!legacy'];
		}

		if(wsrels['!id'].rId1) zip.file(get_rels_path(f), write_rels(wsrels));
	}

	if(opts.Strings != null && opts.Strings.length > 0) {
		f = "xl/sharedStrings." + wbext;
		zip.file(f, write_sst(opts.Strings, f, opts));
		ct.strs.push(f);
		add_rels(opts.wbrels, -1, "sharedStrings." + wbext, RELS.SST);
	}

	/* TODO: something more intelligent with themes */

	f = "xl/theme/theme1.xml";
	zip.file(f, write_theme(wb.Themes, opts));
	ct.themes.push(f);
	add_rels(opts.wbrels, -1, "theme/theme1.xml", RELS.THEME);

	/* TODO: something more intelligent with styles */

	f = "xl/styles." + wbext;
	zip.file(f, write_sty(wb, f, opts));
	ct.styles.push(f);
	add_rels(opts.wbrels, -1, "styles." + wbext, RELS.STY);

	if(wb.vbaraw && vbafmt) {
		f = "xl/vbaProject.bin";
		zip.file(f, wb.vbaraw);
		ct.vba.push(f);
		add_rels(opts.wbrels, -1, "vbaProject.bin", RELS.VBA);
	}

	zip.file("[Content_Types].xml", write_ct(ct, opts));
	zip.file('_rels/.rels', write_rels(opts.rels));
	zip.file('xl/_rels/workbook.' + wbext + '.rels', write_rels(opts.wbrels));

	delete opts.revssf; delete opts.ssf;
	return zip;
}
function firstbyte(f,o) {
	var x = "";
	switch((o||{}).type || "base64") {
		case 'buffer': return [f[0], f[1], f[2], f[3]];
		case 'base64': x = Base64.decode(f.substr(0,24)); break;
		case 'binary': x = f; break;
		case 'array':  return [f[0], f[1], f[2], f[3]];
		default: throw new Error("Unrecognized type " + (o ? o.type : "undefined"));
	}
	return [x.charCodeAt(0), x.charCodeAt(1), x.charCodeAt(2), x.charCodeAt(3)];
}

function read_cfb(cfb, opts) {
	if(cfb.find("EncryptedPackage")) return parse_xlsxcfb(cfb, opts);
	return parse_xlscfb(cfb, opts);
}

function read_zip(data, opts) {
var zip, d = data;
	var o = opts||{};
	if(!o.type) o.type = (has_buf && Buffer.isBuffer(data)) ? "buffer" : "base64";
	switch(o.type) {
		case "base64": zip = new jszip(d, { base64:true }); break;
		case "binary": case "array": zip = new jszip(d, { base64:false }); break;
		case "buffer": zip = new jszip(d); break;
		default: throw new Error("Unrecognized type " + o.type);
	}
	return parse_zip(zip, o);
}

function read_utf16(data, o) {
	var d = data;
	if(o.type == 'base64') d = Base64.decode(d);
	d = cptable.utils.decode(1200, d.slice(2));
	o.type = "binary";
	if(d.charCodeAt(0) == 0x3C) return parse_xlml(d,o);
	return PRN.to_workbook(d, o);
}

function readSync(data, opts) {
	var zip, d = data, n=[0];
	var o = opts||{};
	_ssfopts = {};
	if(o.dateNF) _ssfopts.dateNF = o.dateNF;
	if(!o.type) o.type = (has_buf && Buffer.isBuffer(data)) ? "buffer" : "base64";
	if(o.type == "file") { o.type = "buffer"; d = _fs.readFileSync(data); }
	switch((n = firstbyte(d, o))[0]) {
		case 0xD0: return read_cfb(CFB.read(d, o), o);
		case 0x09: return parse_xlscfb(s2a(o.type === 'base64' ? Base64.decode(d) : d), o);
		case 0x3C: return parse_xlml(d, o);
		case 0x49: if(n[1] == 0x44) return read_wb_ID(d, o); break;
		case 0x54: if(n[1] == 0x41 && n[2] == 0x42 && n[3] == 0x4C) return DIF.to_workbook(d, o); break;
		case 0x50: if(n[1] == 0x4B && n[2] < 0x20 && n[3] < 0x20) return read_zip(d, o); break;
		case 0xEF: return n[3] == 0x3C ? parse_xlml(d, o) : PRN.to_workbook(d,o);
		case 0xFF: if(n[1] == 0xFE){ return read_utf16(d, o); } break;
		case 0x00: if(n[1] == 0x00 && n[2] >= 0x02 && n[3] == 0x00) return WK_.to_workbook(d, o); break;
		case 0x03: case 0x83: case 0x8B: return DBF.to_workbook(d, o);
	}
	if(n[2] <= 12 && n[3] <= 31) return DBF.to_workbook(d, o);
	if(0x20>n[0]||n[0]>0x7F) throw new Error("Unsupported file " + n.join("|"));
	return PRN.to_workbook(d, o);
}

function readFileSync(filename, opts) {
	var o = opts||{}; o.type = 'file';
	return readSync(filename, o);
}
function write_zip_type(wb, opts) {
	var o = opts||{};
	var z = write_zip(wb, o);
	var oopts = {};
	if(o.compression) oopts.compression = 'DEFLATE';
	switch(o.type) {
		case "base64": oopts.type = "base64"; break;
		case "binary": oopts.type = "string"; break;
		case "buffer":
		case "file": oopts.type = "nodebuffer"; break;
		default: throw new Error("Unrecognized type " + o.type);
	}
	if(o.type === "file") return _fs.writeFileSync(o.file, z.generate(oopts));
	return z.generate(oopts);
}

/* TODO: test consistency */
function write_bstr_type(out, opts) {
	switch(opts.type) {
		case "base64": return Base64.encode(out);
		case "binary": return out;
		case "file": return _fs.writeFileSync(opts.file, out, 'binary');
		case "buffer": {
			if(has_buf) return new Buffer(out, 'utf8');
			else return out.split("").map(function(c) { return c.charCodeAt(0); });
		}
	}
	throw new Error("Unrecognized type " + opts.type);
}

/* TODO: test consistency */
function write_string_type(out, opts) {
	switch(opts.type) {
		case "base64": return Base64.encode(out);
		case "binary": return out;
		case "file": return _fs.writeFileSync(opts.file, out, 'utf8');
		case "buffer": {
			if(has_buf) return new Buffer(out, 'utf8');
			else return out.split("").map(function(c) { return c.charCodeAt(0); });
		}
	}
	throw new Error("Unrecognized type " + opts.type);
}

/* TODO: test consistency */
function write_binary_type(out, opts) {
	switch(opts.type) {
		case "base64":
		case "binary":
			var bstr = "";
			for(var i = 0; i < out.length; ++i) bstr += String.fromCharCode(out[i]);
			return opts.type == 'base64' ? Base64.encode(bstr) : bstr;
		case "file": return _fs.writeFileSync(opts.file, out);
		case "buffer": return out;
		default: throw new Error("Unrecognized type " + opts.type);
	}
}

function writeSync(wb, opts) {
	check_wb(wb);
	var o = opts||{};
	switch(o.bookType || 'xlsb') {
		case 'xml':
		case 'xlml': return write_string_type(write_xlml(wb, o), o);
		case 'slk':
		case 'sylk': return write_string_type(write_slk_str(wb, o), o);
		case 'html': return write_string_type(write_htm_str(wb, o), o);
		case 'txt': return write_bstr_type(write_txt_str(wb, o), o);
		case 'csv': return write_string_type(write_csv_str(wb, o), o);
		case 'dif': return write_string_type(write_dif_str(wb, o), o);
		case 'prn': return write_string_type(write_prn_str(wb, o), o);
		case 'fods': return write_string_type(write_ods(wb, o), o);
		case 'biff2': return write_binary_type(write_biff_buf(wb, o), o);
		case 'xlsx':
		case 'xlsm':
		case 'xlsb':
		case 'ods': return write_zip_type(wb, o);
		default: throw new Error ("Unrecognized bookType |" + o.bookType + "|");
	}
}

function resolve_book_type(o/*?WriteFileOpts*/) {
	if(!o.bookType) switch(o.file.slice(o.file.lastIndexOf(".")).toLowerCase()) {
		case '.xlsx': o.bookType = 'xlsx'; break;
		case '.xlsm': o.bookType = 'xlsm'; break;
		case '.xlsb': o.bookType = 'xlsb'; break;
		case '.fods': o.bookType = 'fods'; break;
		case '.xlml': o.bookType = 'xlml'; break;
		case '.sylk': o.bookType = 'sylk'; break;
		case '.html': o.bookType = 'html'; break;
		case '.xls': o.bookType = 'biff2'; break;
		case '.xml': o.bookType = 'xml'; break;
		case '.ods': o.bookType = 'ods'; break;
		case '.csv': o.bookType = 'csv'; break;
		case '.txt': o.bookType = 'txt'; break;
		case '.dif': o.bookType = 'dif'; break;
		case '.prn': o.bookType = 'prn'; break;
		case '.slk': o.bookType = 'sylk'; break;
		case '.htm': o.bookType = 'html'; break;
	}
}

function writeFileSync(wb, filename, opts) {
	var o = opts||{}; o.type = 'file';
	o.file = filename;
	resolve_book_type(o);
	return writeSync(wb, o);
}

function writeFileAsync(filename, wb, opts, cb) {
	var o = opts||{}; o.type = 'file';
	o.file = filename;
	resolve_book_type(o);
	o.type = 'buffer';
	var _cb = cb; if(!(_cb instanceof Function)) _cb = (opts);
	return _fs.writeFile(filename, writeSync(wb, o), _cb);
}
function sheet_to_json(sheet, opts){
	if(sheet == null || sheet["!ref"] == null) return [];
	var val = {t:'n',v:0}, header = 0, offset = 1, hdr = [], isempty = true, v=0, vv="";
	var r = {s:{r:0,c:0},e:{r:0,c:0}};
	var o = opts != null ? opts : {};
	var raw = o.raw;
	var defval = o.defval;
	var range = o.range != null ? o.range : sheet["!ref"];
	if(o.header === 1) header = 1;
	else if(o.header === "A") header = 2;
	else if(Array.isArray(o.header)) header = 3;
	switch(typeof range) {
		case 'string': r = safe_decode_range(range); break;
		case 'number': r = safe_decode_range(sheet["!ref"]); r.s.r = range; break;
		default: r = range;
	}
	if(header > 0) offset = 0;
	var rr = encode_row(r.s.r);
	var cols = new Array(r.e.c-r.s.c+1);
	var out = new Array(r.e.r-r.s.r-offset+1);
	var outi = 0, counter = 0;
	var dense = Array.isArray(sheet);
	var R = r.s.r, C = 0, CC = 0;
	if(dense && !sheet[R]) sheet[R] = [];
	for(C = r.s.c; C <= r.e.c; ++C) {
		cols[C] = encode_col(C);
		val = dense ? sheet[R][C] : sheet[cols[C] + rr];
		switch(header) {
			case 1: hdr[C] = C - r.s.c; break;
			case 2: hdr[C] = cols[C]; break;
			case 3: hdr[C] = o.header[C - r.s.c]; break;
			default:
				if(val == null) continue;
				vv = v = format_cell(val, null, o);
				counter = 0;
				for(CC = 0; CC < hdr.length; ++CC) if(hdr[CC] == vv) vv = v + "_" + (++counter);
				hdr[C] = vv;
		}
	}
	var row = (header === 1) ? [] : {};
	for (R = r.s.r + offset; R <= r.e.r; ++R) {
		rr = encode_row(R);
		isempty = true;
		if(header === 1) row = [];
		else {
			row = {};
			if(Object.defineProperty) try { Object.defineProperty(row, '__rowNum__', {value:R, enumerable:false}); } catch(e) { row.__rowNum__ = R; }
			else row.__rowNum__ = R;
		}
		if(!dense || sheet[R]) for (C = r.s.c; C <= r.e.c; ++C) {
			val = dense ? sheet[R][C] : sheet[cols[C] + rr];
			if(val === undefined || val.t === undefined) {
				if(defval === undefined) continue;
				if(hdr[C] != null) { row[hdr[C]] = defval; isempty = false; }
				continue;
			}
			v = val.v;
			switch(val.t){
				case 'z': if(v == null) break; continue;
				case 'e': continue;
				case 's': case 'd': case 'b': case 'n': break;
				default: throw new Error('unrecognized type ' + val.t);
			}
			if(hdr[C] != null) {
				if(v == null) {
					if(defval !== undefined) row[hdr[C]] = defval;
					else if(raw && v === null) row[hdr[C]] = null;
					else continue;
				} else {
					row[hdr[C]] = raw ? v : format_cell(val,v,o);
				}
				isempty = false;
			}
		}
		if((isempty === false) || (header === 1 ? o.blankrows !== false : !!o.blankrows)) out[outi++] = row;
	}
	out.length = outi;
	return out;
}

var qreg = /"/g;
function make_csv_row(sheet, r, R, cols, fs, rs, FS, o) {
	var isempty = true;
	var row = "", txt = "", rr = encode_row(R);
	for(var C = r.s.c; C <= r.e.c; ++C) {
		var val = o.dense ? (sheet[R]||[])[C]: sheet[cols[C] + rr];
		if(val == null) txt = "";
		else if(val.v != null) {
			isempty = false;
			txt = ''+format_cell(val, null, o);
			for(var i = 0, cc = 0; i !== txt.length; ++i) if((cc = txt.charCodeAt(i)) === fs || cc === rs || cc === 34) {txt = "\"" + txt.replace(qreg, '""') + "\""; break; }
			if(txt == "ID") txt = '"ID"';
		} else if(val.f != null && !val.F) {
			isempty = false;
			txt = '=' + val.f; if(txt.indexOf(",") >= 0) txt = '"' + txt.replace(qreg, '""') + '"';
		} else txt = "";
		/* NOTE: Excel CSV does not support array formulae */
		row += (C === r.s.c ? "" : FS) + txt;
	}
	if(o.blankrows === false && isempty) return null;
	return row;
}

function sheet_to_csv(sheet, opts) {
	var out = [];
	var o = opts == null ? {} : opts;
	if(sheet == null || sheet["!ref"] == null) return "";
	var r = safe_decode_range(sheet["!ref"]);
	var FS = o.FS !== undefined ? o.FS : ",", fs = FS.charCodeAt(0);
	var RS = o.RS !== undefined ? o.RS : "\n", rs = RS.charCodeAt(0);
	var endregex = new RegExp((FS=="|" ? "\\|" : FS)+"+$");
	var row = "", cols = [];
	o.dense = Array.isArray(sheet);
	for(var C = r.s.c; C <= r.e.c; ++C) cols[C] = encode_col(C);
	for(var R = r.s.r; R <= r.e.r; ++R) {
		row = make_csv_row(sheet, r, R, cols, fs, rs, FS, o);
		if(row == null) { continue; }
		if(o.strip) row = row.replace(endregex,"");
		out.push(row + RS);
	}
	delete o.dense;
	return out.join("");
}

function sheet_to_txt(sheet, opts) {
	if(!opts) opts = {}; opts.FS = "\t"; opts.RS = "\n";
	var s = sheet_to_csv(sheet, opts);
	if(typeof cptable == 'undefined') return s;
	var o = cptable.utils.encode(1200, s);
	return "\xff\xfe" + o;
}

function sheet_to_formulae(sheet) {
	var y = "", x, val="";
	if(sheet == null || sheet["!ref"] == null) return [];
	var r = safe_decode_range(sheet['!ref']), rr = "", cols = [], C;
	var cmds = new Array((r.e.r-r.s.r+1)*(r.e.c-r.s.c+1));
	var i = 0;
	var dense = Array.isArray(sheet);
	for(C = r.s.c; C <= r.e.c; ++C) cols[C] = encode_col(C);
	for(var R = r.s.r; R <= r.e.r; ++R) {
		rr = encode_row(R);
		for(C = r.s.c; C <= r.e.c; ++C) {
			y = cols[C] + rr;
			x = dense ? (sheet[R]||[])[C] : sheet[y];
			val = "";
			if(x === undefined) continue;
			else if(x.F != null) {
				y = x.F;
				if(!x.f) continue;
				val = x.f;
				if(y.indexOf(":") == -1) y = y + ":" + y;
			}
			if(x.f != null) val = x.f;
			else if(x.t == 'z') continue;
			else if(x.t == 'n' && x.v != null) val = "" + x.v;
			else if(x.t == 'b') val = x.v ? "TRUE" : "FALSE";
			else if(x.w !== undefined) val = "'" + x.w;
			else if(x.v === undefined) continue;
			else if(x.t == 's') val = "'" + x.v;
			else val = ""+x.v;
			cmds[i++] = y + "=" + val;
		}
	}
	cmds.length = i;
	return cmds;
}

function json_to_sheet(js, opts) {
	var o = opts || {};
	var ws = ({});
	var cell;
	var range = ({s: {c:0, r:0}, e: {c:0, r:js.length}});
	var hdr = o.header || [], C = 0;

	for(var R = 0; R != js.length; ++R) {
		Object.keys(js[R]).filter(function(x) { return js[R].hasOwnProperty(x); }).forEach(function(k) {
			if((C=hdr.indexOf(k)) == -1) hdr[C=hdr.length] = k;
			var v = js[R][k];
			var t = 'z';
			var z = "";
			if(typeof v == 'number') t = 'n';
			else if(typeof v == 'boolean') t = 'b';
			else if(typeof v == 'string') t = 's';
			else if(v instanceof Date) {
				t = 'd';
				if(!o.cellDates) { t = 'n'; v = datenum(v); }
				z = o.dateNF || SSF._table[14];
			}
			ws[encode_cell({c:C,r:R+1})] = cell = ({t:t, v:v});
			if(z) cell.z = z;
		});
	}
	range.e.c = hdr.length - 1;
	for(C = 0; C < hdr.length; ++C) ws[encode_col(C) + "1"] = {t:'s', v:hdr[C]};
	ws['!ref'] = encode_range(range);
	return ws;
}

var utils = {
	encode_col: encode_col,
	encode_row: encode_row,
	encode_cell: encode_cell,
	encode_range: encode_range,
	decode_col: decode_col,
	decode_row: decode_row,
	split_cell: split_cell,
	decode_cell: decode_cell,
	decode_range: decode_range,
	format_cell: format_cell,
	get_formulae: sheet_to_formulae,
	make_csv: sheet_to_csv,
	make_json: sheet_to_json,
	make_formulae: sheet_to_formulae,
	aoa_to_sheet: aoa_to_sheet,
	json_to_sheet: json_to_sheet,
	table_to_sheet: parse_dom_table,
	table_to_book: table_to_book,
	sheet_to_csv: sheet_to_csv,
	sheet_to_json: sheet_to_json,
	sheet_to_html: HTML_.from_sheet,
	sheet_to_formulae: sheet_to_formulae,
	sheet_to_row_object_array: sheet_to_json
};

(function(utils) {
utils.consts = utils.consts || {};
function add_consts(R/*Array<any>*/) { R.forEach(function(a){ utils.consts[a[0]] = a[1]; }); }

function get_default(x, y, z) { return x[y] != null ? x[y] : (x[y] = z); }

/* get cell, creating a stub if necessary */
function ws_get_cell_stub(ws, R, C) {
	/* A1 cell address */
	if(typeof R == "string") return ws[R] || (ws[R] = {t:'z'});
	/* cell address object */
	if(typeof R != "number") return ws_get_cell_stub(ws, encode_cell(R));
	/* R and C are 0-based indices */
	return ws_get_cell_stub(ws, encode_cell({r:R,c:C||0}));
}

/* find sheet index for given name / validate index */
function wb_sheet_idx(wb, sh) {
	if(typeof sh == "number") {
		if(sh >= 0 && wb.SheetNames.length > sh) return sh;
		throw new Error("Cannot find sheet # " + sh);
	} else if(typeof sh == "string") {
		var idx = wb.SheetNames.indexOf(sh);
		if(idx > -1) return idx;
		throw new Error("Cannot find sheet name |" + sh + "|");
	} else throw new Error("Cannot find sheet |" + sh + "|");
}

/* simple blank workbook object */
utils.book_new = function() {
	return { SheetNames: [], Sheets: {} };
};

/* add a worksheet to the end of a given workbook */
utils.book_append_sheet = function(wb, ws, name) {
	if(!name) for(var i = 1; i <= 0xFFFF; ++i) if(wb.SheetNames.indexOf(name = "Sheet" + i) == -1) break;
	if(!name) throw new Error("Too many worksheets");
	check_ws_name(name);
	if(wb.SheetNames.indexOf(name) >= 0) throw new Error("Worksheet with name |" + name + "| already exists!");

	wb.SheetNames.push(name);
	wb.Sheets[name] = ws;
};

/* set sheet visibility (visible/hidden/very hidden) */
utils.book_set_sheet_visibility = function(wb, sh, vis) {
	get_default(wb,"Workbook",{});
	get_default(wb.Workbook,"Sheets",[]);

	var idx = wb_sheet_idx(wb, sh);
	// $FlowIgnore
	get_default(wb.Workbook.Sheets,idx, {});

	switch(vis) {
		case 0: case 1: case 2: break;
		default: throw new Error("Bad sheet visibility setting " + vis);
	}
	// $FlowIgnore
	wb.Workbook.Sheets[idx].Hidden = vis;
};
add_consts([
	["SHEET_VISIBLE", 0],
	["SHEET_HIDDEN", 1],
	["SHEET_VERY_HIDDEN", 2]
]);

/* set number format */
utils.cell_set_number_format = function(cell, fmt) {
	cell.z = fmt;
	return cell;
};

/* set cell hyperlink */
utils.cell_set_hyperlink = function(cell, target, tooltip) {
	if(!target) {
		delete cell.l;
	} else {
		cell.l = ({ Target: target });
		if(tooltip) cell.l.Tooltip = tooltip;
	}
	return cell;
};

/* add to cell comments */
utils.cell_add_comment = function(cell, text, author) {
	if(!cell.c) cell.c = [];
	cell.c.push({t:text, a:author||"SheetJS"});
};

/* set array formula and flush related cells */
utils.sheet_set_array_formula = function(ws, range, formula) {
	var rng = typeof range != "string" ? range : safe_decode_range(range);
	var rngstr = typeof range == "string" ? range : encode_range(range);
	for(var R = rng.s.r; R <= rng.e.r; ++R) for(var C = rng.s.c; C <= rng.e.c; ++C) {
		var cell = ws_get_cell_stub(ws, R, C);
		cell.t = 'n';
		cell.F = rngstr;
		delete cell.v;
		if(R == rng.s.r && C == rng.s.c) cell.f = formula;
	}
	return ws;
};

return utils;
})(utils);

if(has_buf && typeof require != 'undefined') (function() {
	var Readable = require('stream').Readable;

	var write_csv_stream = function(sheet, opts) {
		var stream = Readable();
		var out = "";
		var o = opts == null ? {} : opts;
		if(sheet == null || sheet["!ref"] == null) { stream.push(null); return stream; }
		var r = safe_decode_range(sheet["!ref"]);
		var FS = o.FS !== undefined ? o.FS : ",", fs = FS.charCodeAt(0);
		var RS = o.RS !== undefined ? o.RS : "\n", rs = RS.charCodeAt(0);
		var endregex = new RegExp((FS=="|" ? "\\|" : FS)+"+$");
		var row = "", cols = [];
		o.dense = Array.isArray(sheet);
		for(var C = r.s.c; C <= r.e.c; ++C) cols[C] = encode_col(C);
		var R = r.s.r;
		stream._read = function() {
			if(R > r.e.r) return stream.push(null);
			while(R <= r.e.r) {
				row = make_csv_row(sheet, r, R, cols, fs, rs, FS, o);
				++R;
				if(row != null) {
					if(o.strip) row = row.replace(endregex,"");
					stream.push(row + RS);
					break;
				}
			}
		};
		return stream;
	};

	var write_html_stream = function(sheet, opts) {
		var stream = Readable();

		var o = opts == null ? {} : opts;
		var r = decode_range(sheet['!ref']), cell;
		o.dense = Array.isArray(sheet);
		stream.push(HTML_.BEGIN);

		var R = r.s.r;
		var end = false;
		stream._read = function() {
			if(R > r.e.r) {
				if(!end) { end = true; stream.push(HTML_.END); }
				return stream.push(null);
			}
			while(R <= r.e.r) {
				stream.push(HTML_._row(sheet, r, R, o));
				++R;
				break;
			}
		};
		return stream;
	};

	XLSX.stream = {
		to_html: write_html_stream,
		to_csv: write_csv_stream
	};
})();

XLSX.parse_xlscfb = parse_xlscfb;
XLSX.parse_ods = parse_ods;
XLSX.parse_fods = parse_fods;
XLSX.write_ods = write_ods;
XLSX.parse_zip = parse_zip;
XLSX.read = readSync; //xlsread
XLSX.readFile = readFileSync; //readFile
XLSX.readFileSync = readFileSync;
XLSX.write = writeSync;
XLSX.writeFile = writeFileSync;
XLSX.writeFileSync = writeFileSync;
XLSX.writeFileAsync = writeFileAsync;
XLSX.utils = utils;
XLSX.SSF = SSF;
})(typeof exports !== 'undefined' ? exports : XLSX);
/*exported XLS */
var XLS = XLSX;
/*exported ODS */
var ODS = XLSX;
