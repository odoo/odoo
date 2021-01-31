/*
 * JQuery zTree exHideNodes v3.5.36
 * http://treejs.cn/
 *
 * Copyright (c) 2010 Hunter.z
 *
 * Licensed same as jquery - MIT License
 * http://www.opensource.org/licenses/mit-license.php
 *
 * email: hunter.z@263.net
 * Date: 2018-06-26
 */
(function($){
  var _setting = {
    data: {
      key: {
        isHidden: "isHidden"
      }
    }
  };
	//default init node of exLib
	var _initNode = function(setting, level, n, parentNode, isFirstNode, isLastNode, openFlag) {
		var isHidden = data.isHidden(setting, n);
		data.isHidden(setting, n, isHidden);
		data.initHideForExCheck(setting, n);
	},
	//add dom for check
	_beforeA = function(setting, node, html) {},
	//update zTreeObj, add method of exLib
	_zTreeTools = function(setting, zTreeTools) {
		zTreeTools.showNodes = function(nodes, options) {
			view.showNodes(setting, nodes, options);
		}
		zTreeTools.showNode = function(node, options) {
			if (!node) {
				return;
			}
			view.showNodes(setting, [node], options);
		}
		zTreeTools.hideNodes = function(nodes, options) {
			view.hideNodes(setting, nodes, options);
		}
		zTreeTools.hideNode = function(node, options) {
			if (!node) {
				return;
			}
			view.hideNodes(setting, [node], options);
		}

		var _checkNode = zTreeTools.checkNode;
		if (_checkNode) {
			zTreeTools.checkNode = function(node, checked, checkTypeFlag, callbackFlag) {
				if (!!node && !!data.isHidden(setting, node)) {
					return;
				}
				_checkNode.apply(zTreeTools, arguments);
			}
		}
	},
	//method of operate data
	_data = {
		initHideForExCheck: function(setting, n) {
      var isHidden = data.isHidden(setting, n);
			if (isHidden && setting.check && setting.check.enable) {
				if(typeof n._nocheck == "undefined") {
					n._nocheck = !!n.nocheck
					n.nocheck = true;
				}
				n.check_Child_State = -1;
				if (view.repairParentChkClassWithSelf) {
					view.repairParentChkClassWithSelf(setting, n);
				}
			}
		},
		initShowForExCheck: function(setting, n) {
      var isHidden = data.isHidden(setting, n);
			if (!isHidden && setting.check && setting.check.enable) {
				if(typeof n._nocheck != "undefined") {
					n.nocheck = n._nocheck;
					delete n._nocheck;
				}
				if (view.setChkClass) {
					var checkObj = $$(n, consts.id.CHECK, setting);
					view.setChkClass(setting, checkObj, n);
				}
				if (view.repairParentChkClassWithSelf) {
					view.repairParentChkClassWithSelf(setting, n);
				}
			}
		}
	},
	//method of operate ztree dom
	_view = {
		clearOldFirstNode: function(setting, node) {
			var n = node.getNextNode();
			while(!!n){
				if (n.isFirstNode) {
					n.isFirstNode = false;
					view.setNodeLineIcos(setting, n);
					break;
				}
				if (n.isLastNode) {
					break;
				}
				n = n.getNextNode();
			}
		},
        clearOldLastNode: function(setting, node, openFlag) {
            var n = node.getPreNode();
            while(!!n){
                if (n.isLastNode) {
                    n.isLastNode = false;
                    if (openFlag) {
                        view.setNodeLineIcos(setting, n);
                    }
                    break;
                }
                if (n.isFirstNode) {
                    break;
                }
                n = n.getPreNode();
            }
        },
		makeDOMNodeMainBefore: function(html, setting, node) {
      var isHidden = data.isHidden(setting, node);
			html.push("<li ", (isHidden ? "style='display:none;' " : ""), "id='", node.tId, "' class='", consts.className.LEVEL, node.level,"' tabindex='0' hidefocus='true' treenode>");
		},
		showNode: function(setting, node, options) {
      data.isHidden(setting, node, false);
			data.initShowForExCheck(setting, node);
			$$(node, setting).show();
		},
		showNodes: function(setting, nodes, options) {
			if (!nodes || nodes.length == 0) {
				return;
			}
			var pList = {}, i, j;
			for (i=0, j=nodes.length; i<j; i++) {
				var n = nodes[i];
				if (!pList[n.parentTId]) {
					var pn = n.getParentNode();
					pList[n.parentTId] = (pn === null) ? data.getRoot(setting) : n.getParentNode();
				}
				view.showNode(setting, n, options);
			}
			for (var tId in pList) {
				var children = data.nodeChildren(setting, pList[tId]);
				view.setFirstNodeForShow(setting, children);
				view.setLastNodeForShow(setting, children);
			}
		},
		hideNode: function(setting, node, options) {
      data.isHidden(setting, node, true);
			node.isFirstNode = false;
			node.isLastNode = false;
			data.initHideForExCheck(setting, node);
			view.cancelPreSelectedNode(setting, node);
			$$(node, setting).hide();
		},
		hideNodes: function(setting, nodes, options) {
			if (!nodes || nodes.length == 0) {
				return;
			}
			var pList = {}, i, j;
			for (i=0, j=nodes.length; i<j; i++) {
				var n = nodes[i];
				if ((n.isFirstNode || n.isLastNode) && !pList[n.parentTId]) {
					var pn = n.getParentNode();
					pList[n.parentTId] = (pn === null) ? data.getRoot(setting) : n.getParentNode();
				}
				view.hideNode(setting, n, options);
			}
			for (var tId in pList) {
				var children = data.nodeChildren(setting, pList[tId]);
				view.setFirstNodeForHide(setting, children);
				view.setLastNodeForHide(setting, children);
			}
		},
		setFirstNode: function(setting, parentNode) {
      var children = data.nodeChildren(setting, parentNode);
      var isHidden = data.isHidden(setting, children[0], false);
			if (children.length > 0 && !isHidden) {
        children[0].isFirstNode = true;
			} else if (children.length > 0) {
				view.setFirstNodeForHide(setting, children);
			}
		},
		setLastNode: function(setting, parentNode) {
      var children = data.nodeChildren(setting, parentNode);
      var isHidden = data.isHidden(setting, children[0]);
			if (children.length > 0 && !isHidden) {
        children[children.length - 1].isLastNode = true;
			} else if (children.length > 0) {
				view.setLastNodeForHide(setting, children);
			}
		},
		setFirstNodeForHide: function(setting, nodes) {
			var n,i,j;
			for (i=0, j=nodes.length; i<j; i++) {
				n = nodes[i];
				if (n.isFirstNode) {
					break;
				}
        var isHidden = data.isHidden(setting, n);
				if (!isHidden && !n.isFirstNode) {
					n.isFirstNode = true;
					view.setNodeLineIcos(setting, n);
					break;
				} else {
					n = null;
				}
			}
			return n;
		},
		setFirstNodeForShow: function(setting, nodes) {
			var n,i,j, first, old;
			for(i=0, j=nodes.length; i<j; i++) {
				n = nodes[i];
        var isHidden = data.isHidden(setting, n);
				if (!first && !isHidden && n.isFirstNode) {
					first = n;
					break;
				} else if (!first && !isHidden && !n.isFirstNode) {
					n.isFirstNode = true;
					first = n;
					view.setNodeLineIcos(setting, n);
				} else if (first && n.isFirstNode) {
					n.isFirstNode = false;
					old = n;
					view.setNodeLineIcos(setting, n);
					break;
				} else {
					n = null;
				}
			}
			return {"new":first, "old":old};
		},
		setLastNodeForHide: function(setting, nodes) {
			var n,i;
			for (i=nodes.length-1; i>=0; i--) {
				n = nodes[i];
				if (n.isLastNode) {
					break;
				}
        var isHidden = data.isHidden(setting, n);
				if (!isHidden && !n.isLastNode) {
					n.isLastNode = true;
					view.setNodeLineIcos(setting, n);
					break;
				} else {
					n = null;
				}
			}
			return n;
		},
		setLastNodeForShow: function(setting, nodes) {
			var n,i,j, last, old;
			for (i=nodes.length-1; i>=0; i--) {
				n = nodes[i];
        var isHidden = data.isHidden(setting, n);
				if (!last && !isHidden && n.isLastNode) {
					last = n;
					break;
				} else if (!last && !isHidden && !n.isLastNode) {
					n.isLastNode = true;
					last = n;
					view.setNodeLineIcos(setting, n);
				} else if (last && n.isLastNode) {
					n.isLastNode = false;
					old = n;
					view.setNodeLineIcos(setting, n);
					break;
				} else {
					n = null;
				}
			}
			return {"new":last, "old":old};
		}
	},

	_z = {
		view: _view,
		data: _data
	};
	$.extend(true, $.fn.zTree._z, _z);

	var zt = $.fn.zTree,
	tools = zt._z.tools,
	consts = zt.consts,
	view = zt._z.view,
	data = zt._z.data,
	event = zt._z.event,
	$$ = tools.$;

  data.isHidden = function(setting, node, newIsHidden) {
    if (!node) {
      return false;
    }
    var key = setting.data.key.isHidden;
    if (typeof newIsHidden !== 'undefined') {
      if (typeof newIsHidden === "string") {
        newIsHidden = tools.eqs(checked, "true");
      }
      newIsHidden = !!newIsHidden;
      node[key] = newIsHidden;
    }
    return node[key];
  };

  data.exSetting(_setting);
	data.addInitNode(_initNode);
	data.addBeforeA(_beforeA);
	data.addZTreeTools(_zTreeTools);

//	Override method in core
	var _dInitNode = data.initNode;
    data.initNode = function(setting, level, node, parentNode, isFirstNode, isLastNode, openFlag) {
        var tmpPNode = (parentNode) ? parentNode: data.getRoot(setting),
            children = tmpPNode[setting.data.key.children];
        data.tmpHideFirstNode = view.setFirstNodeForHide(setting, children);
        data.tmpHideLastNode = view.setLastNodeForHide(setting, children);
        if (openFlag) {
            view.setNodeLineIcos(setting, data.tmpHideFirstNode);
            view.setNodeLineIcos(setting, data.tmpHideLastNode);
        }
        isFirstNode = (data.tmpHideFirstNode === node);
        isLastNode = (data.tmpHideLastNode === node);
        if (_dInitNode) _dInitNode.apply(data, arguments);
        if (openFlag && isLastNode) {
            view.clearOldLastNode(setting, node, openFlag);
        }
    };

	var _makeChkFlag = data.makeChkFlag;
	if (!!_makeChkFlag) {
		data.makeChkFlag = function(setting, node) {
			if (!!node && !!data.isHidden(setting, node)) {
				return;
			}
			_makeChkFlag.apply(data, arguments);
		}
	}

	var _getTreeCheckedNodes = data.getTreeCheckedNodes;
	if (!!_getTreeCheckedNodes) {
		data.getTreeCheckedNodes = function(setting, nodes, checked, results) {
			if (!!nodes && nodes.length > 0) {
				var p = nodes[0].getParentNode();
				if (!!p && !!data.isHidden(setting, p)) {
					return [];
				}
			}
			return _getTreeCheckedNodes.apply(data, arguments);
		}
	}

	var _getTreeChangeCheckedNodes = data.getTreeChangeCheckedNodes;
	if (!!_getTreeChangeCheckedNodes) {
		data.getTreeChangeCheckedNodes = function(setting, nodes, results) {
			if (!!nodes && nodes.length > 0) {
				var p = nodes[0].getParentNode();
				if (!!p && !!data.isHidden(setting, p)) {
					return [];
				}
			}
			return _getTreeChangeCheckedNodes.apply(data, arguments);
		}
	}

	var _expandCollapseSonNode = view.expandCollapseSonNode;
	if (!!_expandCollapseSonNode) {
		view.expandCollapseSonNode = function(setting, node, expandFlag, animateFlag, callback) {
			if (!!node && !!data.isHidden(setting, node)) {
				return;
			}
			_expandCollapseSonNode.apply(view, arguments);
		}
	}

	var _setSonNodeCheckBox = view.setSonNodeCheckBox;
	if (!!_setSonNodeCheckBox) {
		view.setSonNodeCheckBox = function(setting, node, value, srcNode) {
			if (!!node && !!data.isHidden(setting, node)) {
				return;
			}
			_setSonNodeCheckBox.apply(view, arguments);
		}
	}

	var _repairParentChkClassWithSelf = view.repairParentChkClassWithSelf;
	if (!!_repairParentChkClassWithSelf) {
		view.repairParentChkClassWithSelf = function(setting, node) {
			if (!!node && !!data.isHidden(setting, node)) {
				return;
			}
			_repairParentChkClassWithSelf.apply(view, arguments);
		}
	}
})(jQuery);