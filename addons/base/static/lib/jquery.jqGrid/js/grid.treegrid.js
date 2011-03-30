;(function($) {
/*
**
 * jqGrid extension - Tree Grid
 * Tony Tomov tony@trirand.com
 * http://trirand.com/blog/ 
 * Dual licensed under the MIT and GPL licenses:
 * http://www.opensource.org/licenses/mit-license.php
 * http://www.gnu.org/licenses/gpl.html
**/ 
$.jgrid.extend({
	setTreeNode : function(rd, row){
		return this.each(function(){
			var $t = this;
			if( !$t.grid || !$t.p.treeGrid ) { return; }
			var expCol = $t.p.expColInd,
			expanded = $t.p.treeReader.expanded_field,
			isLeaf = $t.p.treeReader.leaf_field,
			level = $t.p.treeReader.level_field,
			loaded = $t.p.treeReader.loaded;

			row.level = rd[level];
			
			if($t.p.treeGridModel == 'nested') {
				var lft = rd[$t.p.treeReader.left_field],
				rgt = rd[$t.p.treeReader.right_field];
				if(!rd[isLeaf]) {
				// NS Model
					rd[isLeaf] = (parseInt(rgt,10) === parseInt(lft,10)+1) ? 'true' : 'false';
				}
			} else {
				//row.parent_id = rd[$t.p.treeReader.parent_id_field];
			}
			var curLevel = parseInt(rd[level],10), ident,lftpos;
			if($t.p.tree_root_level === 0) {
				ident = curLevel+1;
				lftpos = curLevel;
			} else {
				ident = curLevel;
				lftpos = curLevel -1;
			}
			var twrap = "<div class='tree-wrap tree-wrap-"+$t.p.direction+"' style='width:"+(ident*18)+"px;'>";
			twrap += "<div style='"+($t.p.direction=="rtl" ? "right:" : "left:")+(lftpos*18)+"px;' class='ui-icon ";

			if(rd[loaded] != undefined) {
				if(rd[loaded]=="true" || rd[loaded]===true) {
					rd[loaded] = true;
				} else {
					rd[loaded] = false;
				}
			}
			if(rd[isLeaf] == "true" || rd[isLeaf] === true) {
				twrap += $t.p.treeIcons.leaf+" tree-leaf'";
				rd[isLeaf] = true;
				rd[expanded] = false;
			} else {
				if(rd[expanded] == "true" || rd[expanded] === true) {
					twrap += $t.p.treeIcons.minus+" tree-minus treeclick'";
					rd[expanded] = true;
				} else {
					twrap += $t.p.treeIcons.plus+" tree-plus treeclick'";
					rd[expanded] = false;
				}
				rd[isLeaf] = false;
			}
			twrap += "</div></div>";
			if(!$t.p.loadonce) {
				rd[$t.p.localReader.id] = row.id;
				$t.p.data.push(rd);
				$t.p._index[row.id]=$t.p.data.length-1;
			}
			if(parseInt(rd[level],10) !== parseInt($t.p.tree_root_level,10)) {                
				if(!$($t).jqGrid("isVisibleNode",rd)){ 
					$(row).css("display","none");
				}
			}
			
			$("td:eq("+expCol+")",row).wrapInner("<span></span>").prepend(twrap);
			$(".treeclick",row).bind("click",function(e){
				var target = e.target || e.srcElement,
				ind2 =$(target,$t.rows).closest("tr.jqgrow")[0].id,
				pos = $t.p._index[ind2],
				isLeaf = $t.p.treeReader.leaf_field,
				expanded = $t.p.treeReader.expanded_field;
				if(!$t.p.data[pos][isLeaf]){
					if($t.p.data[pos][expanded]){
						$($t).jqGrid("collapseRow",$t.p.data[pos]);
						$($t).jqGrid("collapseNode",$t.p.data[pos]);
					} else {
						$($t).jqGrid("expandRow",$t.p.data[pos]);
						$($t).jqGrid("expandNode",$t.p.data[pos]);
					}
				}
				return false;
			});
			if($t.p.ExpandColClick === true) {
			$("span", row).css("cursor","pointer").bind("click",function(e){
				var target = e.target || e.srcElement,
				ind2 =$(target,$t.rows).closest("tr.jqgrow")[0].id,
				pos = $t.p._index[ind2],
				isLeaf = $t.p.treeReader.leaf_field,
				expanded = $t.p.treeReader.expanded_field;
				if(!$t.p.data[pos][isLeaf]){
					if($t.p.data[pos][expanded]){
						$($t).jqGrid("collapseRow",$t.p.data[pos]);
						$($t).jqGrid("collapseNode",$t.p.data[pos]);
					} else {
						$($t).jqGrid("expandRow",$t.p.data[pos]);
						$($t).jqGrid("expandNode",$t.p.data[pos]);
					}
				}
				$($t).jqGrid("setSelection",ind2);
				return false;
			});
			}
		});
	},
	setTreeGrid : function() {
		return this.each(function (){
			var $t = this, i=0, pico;
			if(!$t.p.treeGrid) { return; }
			if(!$t.p.treedatatype ) { $.extend($t.p,{treedatatype: $t.p.datatype}); }
			$t.p.subGrid = false; $t.p.altRows =false;
			$t.p.pgbuttons = false; $t.p.pginput = false;
			$t.p.multiselect = false; $t.p.rowList = [];
			pico = 'ui-icon-triangle-1-' + ($t.p.direction=="rtl" ? 'w' : 'e');
			$t.p.treeIcons = $.extend({plus:pico,minus:'ui-icon-triangle-1-s',leaf:'ui-icon-radio-off'},$t.p.treeIcons || {});
			if($t.p.treeGridModel == 'nested') {
				$t.p.treeReader = $.extend({
					level_field: "level",
					left_field:"lft",
					right_field: "rgt",
					leaf_field: "isLeaf",
					expanded_field: "expanded",
					loaded: "loaded"
				},$t.p.treeReader);
			} else
				if($t.p.treeGridModel == 'adjacency') {
				$t.p.treeReader = $.extend({
						level_field: "level",
						parent_id_field: "parent",
						leaf_field: "isLeaf",
						expanded_field: "expanded",
						loaded: "loaded"
				},$t.p.treeReader );
			}
			for (var key in $t.p.colModel){
				if($t.p.colModel.hasOwnProperty(key)) {
					if($t.p.colModel[key].name == $t.p.ExpandColumn) {
						$t.p.expColInd = i;
						break;
					}
					i++;
				}
			}
			if(!$t.p.expColInd) { $t.p.expColInd = 0; }
			$.each($t.p.treeReader,function(i,n){
				if(n){
					$t.p.colNames.push(n);
					$t.p.colModel.push({name:n,width:1,hidden:true,sortable:false,resizable:false,hidedlg:true,editable:true,search:false});
				}
			});			
		});
	},
	expandRow: function (record){
		this.each(function(){
			var $t = this;
			if(!$t.grid || !$t.p.treeGrid) { return; }
			var childern = $($t).jqGrid("getNodeChildren",record),
			//if ($($t).jqGrid("isVisibleNode",record)) {
			expanded = $t.p.treeReader.expanded_field;
			$(childern).each(function(i){
				var id  = $.jgrid.getAccessor(this,$t.p.localReader.id);
				$("#"+id,$t.grid.bDiv).css("display","");
				if(this[expanded]) {
					$($t).jqGrid("expandRow",this);
				}
			});
			//}
		});
	},
	collapseRow : function (record) {
		this.each(function(){
			var $t = this;
			if(!$t.grid || !$t.p.treeGrid) { return; }
			var childern = $($t).jqGrid("getNodeChildren",record),
			expanded = $t.p.treeReader.expanded_field;
			$(childern).each(function(i){
				var id  = $.jgrid.getAccessor(this,$t.p.localReader.id);
				$("#"+id,$t.grid.bDiv).css("display","none");
				if(this[expanded]){
					$($t).jqGrid("collapseRow",this);
				}
			});
		});
	},
	// NS ,adjacency models
	getRootNodes : function() {
		var result = [];
		this.each(function(){
			var $t = this;
			if(!$t.grid || !$t.p.treeGrid) { return; }
			switch ($t.p.treeGridModel) {
				case 'nested' :
					var level = $t.p.treeReader.level_field;
					$($t.p.data).each(function(i){
						if(parseInt(this[level],10) === parseInt($t.p.tree_root_level,10)) {
							result.push(this);
						}
					});
					break;
				case 'adjacency' :
					var parent_id = $t.p.treeReader.parent_id_field;
					$($t.p.data).each(function(i){
						if(this[parent_id] === null || String(this[parent_id]).toLowerCase() == "null") {
							result.push(this);
						}
					});
					break;
			}
		});
		return result;
	},
	getNodeDepth : function(rc) {
		var ret = null;
		this.each(function(){
			if(!this.grid || !this.p.treeGrid) { return; }
			var $t = this;
			switch ($t.p.treeGridModel) {
				case 'nested' :
					var level = $t.p.treeReader.level_field;
					ret = parseInt(rc[level],10) - parseInt($t.p.tree_root_level,10);
					break;
				case 'adjacency' :
					ret = $($t).jqGrid("getNodeAncestors",rc).length;
					break;
			}
		});
		return ret;
	},
	getNodeParent : function(rc) {
		var result = null;
		this.each(function(){
			var $t = this;
			if(!$t.grid || !$t.p.treeGrid) { return; }
			switch ($t.p.treeGridModel) {
				case 'nested' :
					var lftc = $t.p.treeReader.left_field,
					rgtc = $t.p.treeReader.right_field,
					levelc = $t.p.treeReader.level_field,
					lft = parseInt(rc[lftc],10), rgt = parseInt(rc[rgtc],10), level = parseInt(rc[levelc],10);
					$(this.p.data).each(function(){
						if(parseInt(this[levelc],10) === level-1 && parseInt(this[lftc],10) < lft && parseInt(this[rgtc],10) > rgt) {
							result = this;
							return false;
						}
					});
					break;
				case 'adjacency' :
					var parent_id = $t.p.treeReader.parent_id_field,
					dtid = $t.p.localReader.id;
					$(this.p.data).each(function(i,val){
						if(this[dtid] == rc[parent_id] ) {
							result = this;
							return false;
						}
					});
					break;
			}
		});
		return result;
	},
	getNodeChildren : function(rc) {
		var result = [];
		this.each(function(){
			var $t = this;
			if(!$t.grid || !$t.p.treeGrid) { return; }
			switch ($t.p.treeGridModel) {
				case 'nested' :
					var lftc = $t.p.treeReader.left_field,
					rgtc = $t.p.treeReader.right_field,
					levelc = $t.p.treeReader.level_field,
					lft = parseInt(rc[lftc],10), rgt = parseInt(rc[rgtc],10), level = parseInt(rc[levelc],10);
					$(this.p.data).each(function(i){
						if(parseInt(this[levelc],10) === level+1 && parseInt(this[lftc],10) > lft && parseInt(this[rgtc],10) < rgt) {
							result.push(this);
						}
					});
					break;
				case 'adjacency' :
					var parent_id = $t.p.treeReader.parent_id_field,
					dtid = $t.p.localReader.id;
					$(this.p.data).each(function(i,val){
						if(this[parent_id] == rc[dtid]) {
							result.push(this);
						}
					});
					break;
			}
		});
		return result;
	},
	getFullTreeNode : function(rc) {
		var result = [];
		this.each(function(){
			var $t = this, len;
			if(!$t.grid || !$t.p.treeGrid) { return; }
			switch ($t.p.treeGridModel) {
				case 'nested' :
					var lftc = $t.p.treeReader.left_field,
					rgtc = $t.p.treeReader.right_field,
					levelc = $t.p.treeReader.level_field,
					lft = parseInt(rc[lftc],10), rgt = parseInt(rc[rgtc],10), level = parseInt(rc[levelc],10);
					$(this.p.data).each(function(i){
						if(parseInt(this[levelc],10) >= level && parseInt(this[lftc],10) >= lft && parseInt(this[lftc],10) <= rgt) {
							result.push(this);
						}
					});
					break;
				case 'adjacency' :
					result.push(rc);
					var parent_id = $t.p.treeReader.parent_id_field,
					dtid = $t.p.localReader.id;
					$(this.p.data).each(function(i){
						len = result.length;
						for (i = 0; i < len; i++) {
							if (result[i][dtid] == this[parent_id]) {
								result.push(this);
								break;
							}
						}
					});
					break;
			}
		});
		return result;
	},	
	// End NS, adjacency Model
	getNodeAncestors : function(rc) {
		var ancestors = [];
		this.each(function(){
			if(!this.grid || !this.p.treeGrid) { return; }
			var parent = $(this).jqGrid("getNodeParent",rc);
			while (parent) {
				ancestors.push(parent);
				parent = $(this).jqGrid("getNodeParent",parent);	
			}
		});
		return ancestors;
	},
	isVisibleNode : function(rc) {
		var result = true;
		this.each(function(){
			var $t = this;
			if(!$t.grid || !$t.p.treeGrid) { return; }
			var ancestors = $($t).jqGrid("getNodeAncestors",rc),
			expanded = $t.p.treeReader.expanded_field;
			$(ancestors).each(function(){
				result = result && this[expanded];
				if(!result) {return false;}
			});
		});
		return result;
	},
	isNodeLoaded : function(rc) {
		var result;
		this.each(function(){
			var $t = this;
			if(!$t.grid || !$t.p.treeGrid) { return; }
			var isLeaf = $t.p.treeReader.leaf_field;
			if(rc.loaded !== undefined) {
				result = rc.loaded;
			} else if( rc[isLeaf] || $($t).jqGrid("getNodeChildren",rc).length > 0){
				result = true;
			} else {
				result = false;
			}
		});
		return result;
	},
	expandNode : function(rc) {
		return this.each(function(){
			if(!this.grid || !this.p.treeGrid) { return; }
			var expanded = this.p.treeReader.expanded_field;
			if(!rc[expanded]) {
				var id = $.jgrid.getAccessor(rc,this.p.localReader.id);
				var rc1 = $("#"+id,this.grid.bDiv)[0];
				var position = this.p._index[id];
				if( $(this).jqGrid("isNodeLoaded",this.p.data[position]) ) {
					rc[expanded] = true;
					$("div.treeclick",rc1).removeClass(this.p.treeIcons.plus+" tree-plus").addClass(this.p.treeIcons.minus+" tree-minus");
				} else {
					rc[expanded] = true;
					$("div.treeclick",rc1).removeClass(this.p.treeIcons.plus+" tree-plus").addClass(this.p.treeIcons.minus+" tree-minus");
					this.p.treeANode = rc1.rowIndex;
					this.p.datatype = this.p.treedatatype;
					if(this.p.treeGridModel == 'nested') {
						$(this).jqGrid("setGridParam",{postData:{nodeid:id,n_left:rc.lft,n_right:rc.rgt,n_level:rc.level}});
					} else {
						$(this).jqGrid("setGridParam",{postData:{nodeid:id,parentid:rc.parent_id,n_level:rc.level}});
					}
					$(this).trigger("reloadGrid");
					if(this.p.treeGridModel == 'nested') {
						$(this).jqGrid("setGridParam",{postData:{nodeid:'',n_left:'',n_right:'',n_level:''}});
					} else {
						$(this).jqGrid("setGridParam",{postData:{nodeid:'',parentid:'',n_level:''}}); 
					}
				}
			}
		});
	},
	collapseNode : function(rc) {
		return this.each(function(){
			if(!this.grid || !this.p.treeGrid) { return; }
			if(rc.expanded) {
				rc.expanded = false;
				var id = $.jgrid.getAccessor(rc,this.p.localReader.id);
				var rc1 = $("#"+id,this.grid.bDiv)[0];
				$("div.treeclick",rc1).removeClass(this.p.treeIcons.minus+" tree-minus").addClass(this.p.treeIcons.plus+" tree-plus");
			}
		});
	},
	SortTree : function( sortname, newDir, st, datefmt) {
		return this.each(function(){
			if(!this.grid || !this.p.treeGrid) { return; }
			var i, len,
			rec, records = [], $t = this, query, roots,
			rt = $(this).jqGrid("getRootNodes");
			// Sorting roots
			query = $.jgrid.from(rt);
			query.orderBy(sortname,newDir,st, datefmt);
			roots = query.select();

			// Sorting children
			for (i = 0, len = roots.length; i < len; i++) {
				rec = roots[i];
				records.push(rec);
				$(this).jqGrid("collectChildrenSortTree",records, rec, sortname, newDir,st, datefmt);
			}
			$.each(records, function(index, row) {
				var id  = $.jgrid.getAccessor(this,$t.p.localReader.id);
				$('#'+$t.p.id+ ' tbody tr:eq('+index+')').after($('tr#'+id,$t.grid.bDiv));
			});
			query = null; roots=null;records=null;
		});
	},
	collectChildrenSortTree : function(records, rec, sortname, newDir,st, datefmt) {
		return this.each(function(){
			if(!this.grid || !this.p.treeGrid) { return; }
			var i, len,
			child, ch, query, children;
			ch = $(this).jqGrid("getNodeChildren",rec);
			query = $.jgrid.from(ch);
			query.orderBy(sortname, newDir, st, datefmt);
			children = query.select();
			for (i = 0, len = children.length; i < len; i++) {
				child = children[i];
				records.push(child);
				$(this).jqGrid("collectChildrenSortTree",records, child, sortname, newDir, st, datefmt); 
			}
		});
	},
	// experimental 
	setTreeRow : function(rowid, data) {
		var success=false;
		this.each(function(){
			var t = this;
			if(!t.grid || !t.p.treeGrid) { return; }
			success = $(t).jqGrid("setRowData",rowid,data);
		});
		return success;
	},
	delTreeNode : function (rowid) {
		return this.each(function () {
			var $t = this;
			if(!$t.grid || !$t.p.treeGrid) { return; }
			var rc = $($t).jqGrid("getInd",rowid,true);
			if (rc) {
				var dr = $($t).jqGrid("getNodeChildren",rc);
				if(dr.length>0){
					for (var i=0;i<dr.length;i++){
						$($t).jqGrid("delRowData",dr[i].id);
					}
				}
				$($t).jqGrid("delRowData",rc.id);
			}
		});
	}
});
})(jQuery);