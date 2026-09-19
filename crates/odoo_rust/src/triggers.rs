use std::collections::{HashMap, HashSet};

use pyo3::prelude::*;
use pyo3::types::{PyList, PyTuple};

type FieldId = u32;
type Bucket = (Vec<FieldId>, Vec<FieldId>);
type FieldTriggers = (FieldId, Vec<Bucket>);
type Meta = (bool, bool, u32, u32, u32, u32, u32);

#[derive(Clone, Copy)]
struct FieldMeta {
    is_many2one: bool,
    is_one2many: bool,
    name: u32,
    inverse_name: u32,
    model_name: u32,
    comodel_name: u32,
    // The stored column the field stands for. Every model of a table-
    // inheritance tree keeps its own field for one column, so a cycle closes
    // on the fact, or a self-dependency shared by n siblings costs n! paths.
    fact: u32,
}

struct Graph {
    triggers: HashMap<FieldId, Vec<Bucket>>,
    meta: Vec<FieldMeta>,
}

impl Graph {
    fn cancels(&self, f1: FieldId, f2: FieldId) -> bool {
        let (a, b) = (self.meta[f1 as usize], self.meta[f2 as usize]);
        a.is_many2one
            && b.is_one2many
            && b.inverse_name == a.name
            && a.model_name == b.comodel_name
            && a.comodel_name == b.model_name
    }

    fn concat_paths(&self, prefix: &[FieldId], path: &[FieldId]) -> Vec<FieldId> {
        let (mut left, mut right) = (prefix, path);
        while let (Some(&f1), Some(&f2)) = (left.last(), right.first()) {
            if self.cancels(f1, f2) {
                left = &left[..left.len() - 1];
                right = &right[1..];
            } else {
                break;
            }
        }
        let mut out = Vec::with_capacity(left.len() + right.len());
        out.extend_from_slice(left);
        out.extend_from_slice(right);
        out
    }

    fn fact(&self, field: FieldId) -> FieldId {
        self.meta[field as usize].fact
    }
}

#[derive(Default)]
struct Collected {
    paths: Vec<Vec<FieldId>>,
    slot_of: HashMap<Vec<FieldId>, usize>,
    roots: Vec<Vec<FieldId>>,
    root_sets: Vec<HashSet<FieldId>>,
}

impl Collected {
    fn slot(&mut self, path: Vec<FieldId>) -> usize {
        if let Some(&i) = self.slot_of.get(&path) {
            return i;
        }
        let i = self.paths.len();
        self.slot_of.insert(path.clone(), i);
        self.paths.push(path);
        self.roots.push(Vec::new());
        self.root_sets.push(HashSet::new());
        i
    }
}

struct Walk<'g> {
    graph: &'g Graph,
    collected: Collected,
    seen: HashSet<FieldId>,
    expanded: HashSet<(FieldId, Option<usize>)>,
    visited_memo: HashMap<FieldId, HashSet<FieldId>>,
}

impl Walk<'_> {
    fn collect(&mut self, field: FieldId, prefix: Option<usize>) -> Option<HashSet<FieldId>> {
        if self.expanded.contains(&(field, prefix)) {
            let visited = &self.visited_memo[&field];
            if visited.is_disjoint(&self.seen) {
                return Some(visited.clone());
            }
        }
        let fact = self.graph.fact(field);
        self.seen.insert(fact);
        let mut visited: HashSet<FieldId> = HashSet::from([fact]);
        let mut clean = true;
        let buckets = &self.graph.triggers[&field];
        for (path, targets) in buckets {
            let full_path = match prefix {
                Some(slot) => self.graph.concat_paths(&self.collected.paths[slot], path),
                None => path.clone(),
            };
            let slot = self.collected.slot(full_path);
            for &target in targets {
                if self.collected.root_sets[slot].insert(target) {
                    self.collected.roots[slot].push(target);
                }
            }
            for &target in targets {
                let target_fact = self.graph.fact(target);
                if self.seen.contains(&target_fact) {
                    if !visited.contains(&target_fact) {
                        clean = false;
                    }
                    continue;
                }
                if !self.graph.triggers.contains_key(&target) {
                    continue;
                }
                match self.collect(target, Some(slot)) {
                    None => clean = false,
                    Some(sub) => visited.extend(sub),
                }
            }
        }
        self.seen.remove(&fact);
        if clean {
            self.visited_memo.insert(field, visited.clone());
            self.expanded.insert((field, prefix));
            return Some(visited);
        }
        None
    }
}

#[derive(Default)]
struct Node {
    root: Vec<FieldId>,
    children: Vec<(FieldId, Node)>,
}

impl Node {
    fn child(&mut self, label: FieldId) -> &mut Node {
        let pos = match self.children.iter().position(|(l, _)| *l == label) {
            Some(p) => p,
            None => {
                self.children.push((label, Node::default()));
                self.children.len() - 1
            }
        };
        &mut self.children[pos].1
    }

    fn to_py<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyTuple>> {
        let root = PyList::new(py, &self.root)?;
        let children = PyList::new(
            py,
            self.children
                .iter()
                .map(|(label, node)| -> PyResult<_> { Ok((*label, node.to_py(py)?)) })
                .collect::<PyResult<Vec<_>>>()?,
        )?;
        PyTuple::new(py, [root.into_any(), children.into_any()])
    }
}

fn tree_of(graph: &Graph, field: FieldId) -> Node {
    let mut tree = Node::default();
    if !graph.triggers.contains_key(&field) {
        return tree;
    }
    let mut walk = Walk {
        graph,
        collected: Collected::default(),
        seen: HashSet::new(),
        expanded: HashSet::new(),
        visited_memo: HashMap::new(),
    };
    walk.collect(field, None);
    for (slot, path) in walk.collected.paths.iter().enumerate() {
        let mut current = &mut tree;
        for &label in path {
            current = current.child(label);
        }
        current.root = std::mem::take(&mut walk.collected.roots[slot]);
    }
    tree
}

fn trees_of(graph: &Graph, fields: &[FieldId]) -> Vec<Node> {
    let workers = std::thread::available_parallelism()
        .map(|n| n.get())
        .unwrap_or(1)
        .min(fields.len().max(1));
    if workers <= 1 || fields.len() < 64 {
        return fields.iter().map(|&f| tree_of(graph, f)).collect();
    }
    let chunk = fields.len().div_ceil(workers);
    std::thread::scope(|scope| {
        let handles: Vec<_> = fields
            .chunks(chunk)
            .map(|part| {
                scope.spawn(move || part.iter().map(|&f| tree_of(graph, f)).collect::<Vec<_>>())
            })
            .collect();
        handles
            .into_iter()
            .flat_map(|h| h.join().expect("trigger tree worker panicked"))
            .collect()
    })
}

#[pyfunction]
#[pyo3(signature = (triggers, meta, fields=None))]
pub fn get_trigger_trees<'py>(
    py: Python<'py>,
    triggers: Vec<FieldTriggers>,
    meta: Vec<Meta>,
    fields: Option<Vec<FieldId>>,
) -> PyResult<Bound<'py, PyList>> {
    let nfields = meta.len();
    let declared: Vec<FieldId> = triggers.iter().map(|(dep, _)| *dep).collect();
    let graph = Graph {
        triggers: triggers.into_iter().collect(),
        meta: meta
            .into_iter()
            .map(|(m, o, n, i, mo, co, fact)| FieldMeta {
                is_many2one: m,
                is_one2many: o,
                name: n,
                inverse_name: i,
                model_name: mo,
                comodel_name: co,
                fact,
            })
            .collect(),
    };
    let fields: Vec<FieldId> = match fields {
        Some(f) => f,
        None => declared,
    };
    let in_range = |f: FieldId| (f as usize) < nfields;
    let all_in_range = graph.triggers.iter().all(|(dep, buckets)| {
        in_range(*dep)
            && buckets
                .iter()
                .all(|(path, targets)| path.iter().chain(targets).all(|&f| in_range(f)))
    }) && fields.iter().all(|&f| in_range(f));
    if !all_in_range {
        return Err(pyo3::exceptions::PyIndexError::new_err(
            "get_trigger_trees: a field id is out of range of `meta`",
        ));
    }
    let trees = py.detach(|| trees_of(&graph, &fields));
    PyList::new(
        py,
        fields
            .iter()
            .zip(&trees)
            .map(|(field, node)| -> PyResult<_> { Ok((*field, node.to_py(py)?)) })
            .collect::<PyResult<Vec<_>>>()?,
    )
}

#[cfg(test)]
mod tests {
    use super::{Bucket, FieldMeta, Graph, tree_of};
    use std::collections::HashMap;

    fn plain(m2o: bool, o2m: bool, name: u32, inverse: u32, model: u32, comodel: u32) -> FieldMeta {
        FieldMeta {
            is_many2one: m2o,
            is_one2many: o2m,
            name,
            inverse_name: inverse,
            model_name: model,
            comodel_name: comodel,
            fact: u32::MAX,
        }
    }

    // a field left with no fact is its own fact
    fn graph(edges: &[(u32, &[u32], &[u32])], meta: Vec<FieldMeta>) -> Graph {
        let mut triggers: HashMap<u32, Vec<Bucket>> = HashMap::new();
        for (dep, path, targets) in edges {
            triggers
                .entry(*dep)
                .or_default()
                .push((path.to_vec(), targets.to_vec()));
        }
        let meta = meta
            .into_iter()
            .enumerate()
            .map(|(i, m)| FieldMeta { fact: if m.fact == u32::MAX { i as u32 } else { m.fact }, ..m })
            .collect();
        Graph { triggers, meta }
    }

    fn count(node: &super::Node) -> usize {
        1 + node.children.iter().map(|(_, c)| count(c)).sum::<usize>()
    }

    #[test]
    fn siblings_sharing_one_fact_close_the_cycle_once_and_list_every_sibling() {
        // n copies F_i of one column (fact 0), each depending on itself through
        // its own many2one P_i (facts 1): F_i --[P_j]--> F_j for every i, j.
        let n = 9u32;
        let mut meta: Vec<FieldMeta> = (0..n).map(|_| plain(false, false, 0, 0, 0, 0)).collect();
        meta.iter_mut().for_each(|m| m.fact = 0);
        meta.extend((0..n).map(|i| FieldMeta { fact: 1, ..plain(true, false, 1, 0, i, i) }));
        let edges: Vec<(u32, Vec<u32>, Vec<u32>)> = (0..n)
            .flat_map(|i| (0..n).map(move |j| (i, vec![n + j], vec![j])))
            .collect();
        let borrowed: Vec<(u32, &[u32], &[u32])> =
            edges.iter().map(|(d, p, t)| (*d, p.as_slice(), t.as_slice())).collect();
        let g = graph(&borrowed, meta);
        let tree = tree_of(&g, 0);
        assert_eq!(count(&tree), 1 + n as usize);
        let listed: Vec<u32> = flat(&tree).into_iter().flat_map(|(_, roots)| roots).collect();
        assert_eq!(listed, (0..n).collect::<Vec<_>>());
    }

    fn flat(node: &super::Node) -> Vec<(Vec<u32>, Vec<u32>)> {
        fn walk(node: &super::Node, prefix: &mut Vec<u32>, out: &mut Vec<(Vec<u32>, Vec<u32>)>) {
            out.push((prefix.clone(), node.root.clone()));
            for (label, child) in &node.children {
                prefix.push(*label);
                walk(child, prefix, out);
                prefix.pop();
            }
        }
        let mut out = Vec::new();
        walk(node, &mut Vec::new(), &mut out);
        out
    }

    #[test]
    fn a_chain_collects_every_descendant_into_the_root_in_order() {
        let meta = (0..4).map(|_| plain(false, false, 0, 0, 0, 0)).collect();
        let g = graph(&[(0, &[], &[1]), (1, &[], &[2]), (2, &[], &[3])], meta);
        assert_eq!(flat(&tree_of(&g, 0)), [(vec![], vec![1, 2, 3])]);
    }

    #[test]
    fn a_labelled_path_opens_a_subtree_and_a_diamond_dedups_its_root() {
        let meta = (0..5).map(|_| plain(false, false, 0, 0, 0, 0)).collect();
        let g = graph(&[(0, &[], &[1, 2]), (1, &[4], &[3]), (2, &[4], &[3])], meta);
        assert_eq!(
            flat(&tree_of(&g, 0)),
            [(vec![], vec![1, 2]), (vec![4], vec![3])]
        );
    }

    #[test]
    fn a_many2one_followed_by_its_inverse_one2many_cancels_out() {
        // field 1: many2one named n=1 on model A(=0) to B(=1); field 2: one2many on B to A with inverse n=1
        let meta = vec![
            plain(false, false, 0, 0, 0, 0),
            plain(true, false, 1, 0, 0, 1),
            plain(false, true, 0, 1, 1, 0),
            plain(false, false, 0, 0, 0, 0),
        ];
        let g = graph(&[(0, &[1], &[3]), (3, &[2], &[0])], meta);
        assert_eq!(g.concat_paths(&[1], &[2]), Vec::<u32>::new());
        assert_eq!(g.concat_paths(&[1], &[1]), vec![1, 1]);
        let tree = tree_of(&g, 0);
        assert_eq!(flat(&tree), [(vec![], vec![0]), (vec![1], vec![3])]);
    }

    #[test]
    fn a_cycle_terminates_and_still_lists_every_member_once() {
        let meta = (0..3).map(|_| plain(false, false, 0, 0, 0, 0)).collect();
        let g = graph(&[(0, &[], &[1]), (1, &[], &[2]), (2, &[], &[0])], meta);
        assert_eq!(flat(&tree_of(&g, 0)), [(vec![], vec![1, 2, 0])]);
    }

    #[test]
    fn a_field_with_no_triggers_is_an_empty_tree() {
        let g = graph(&[], vec![plain(false, false, 0, 0, 0, 0)]);
        assert_eq!(flat(&tree_of(&g, 0)), [(vec![], vec![])]);
    }
}
