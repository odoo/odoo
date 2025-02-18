from __future__ import annotations

import ast
from abc import ABC, abstractmethod
import typing

if typing.TYPE_CHECKING:
    from collections.abc import Collection, Iterable


class SetDefinitions:
    """ A collection of set definitions, where each set is defined by an id, a
    name, its supersets, and the sets that are disjoint with it.  This object
    is used as a factory to create set expressions, which are combinations of
    named sets with union, intersection and complement.
    """
    __slots__ = ('__leaves',)

    def __init__(self, definitions: dict[int, dict]):
        """ Initialize the object with ``definitions``, a dict which maps each
        set id to a dict with optional keys ``"ref"`` (value is the set's name),
        ``"supersets"`` (value is a collection of set ids), and ``"disjoints"``
        (value is a collection of set ids).

        Here is an example of set definitions, with natural numbers (N), integer
        numbers (Z), rational numbers (Q), irrational numbers (R\\Q), real
        numbers (R), imaginary numbers (I) and complex numbers (C)::

            {
                1: {"ref": "N", "supersets": [2]},
                2: {"ref": "Z", "supersets": [3]},
                3: {"ref": "Q", "supersets": [4]},
                4: {"ref": "R", "supersets": [6]},
                5: {"ref": "I", "supersets": [6], "disjoints": [4]},
                6: {"ref": "C"},
                7: {"ref": "R\\Q", "supersets": [4]},
            }
            Representation:
            ┌──────────────────────────────────────────┐
            │ C  ┌──────────────────────────┐          │
            │    │ R  ┌───────────────────┐ │ ┌──────┐ |   "C"
            │    │    │ Q  ┌────────────┐ │ │ │ I    | |   "I" implied "C"
            │    │    │    │ Z  ┌─────┐ │ │ │ │      | |   "R" implied "C"
            │    │    │    │    │ N   │ │ │ │ │      │ │   "Q" implied "R"
            │    │    │    │    └─────┘ │ │ │ │      │ │   "R\\Q" implied "R"
            │    │    │    └────────────┘ │ │ │      │ │   "Z" implied "Q"
            │    │    └───────────────────┘ │ │      │ │   "N" implied "Z"
            │    │      ┌───────────────┐   │ │      │ │
            │    │      │ R\\Q          │   │ │      │ │
            │    │      └───────────────┘   │ └──────┘ │
            │    └──────────────────────────┘          │
            └──────────────────────────────────────────┘
        """
        self.__leaves: dict[int | str, Leaf] = {}

        for leaf_id, info in definitions.items():
            ref = info['ref']
            assert ref != '*', "The set reference '*' is reserved for the universal set."
            leaf = Leaf(leaf_id, ref)
            self.__leaves[leaf_id] = leaf
            self.__leaves[ref] = leaf

        # compute transitive closure of subsets and supersets
        subsets = {leaf.id: leaf.subsets for leaf in self.__leaves.values()}
        supersets = {leaf.id: leaf.supersets for leaf in self.__leaves.values()}
        for leaf_id, info in definitions.items():
            for greater_id in info.get('supersets', ()):
                # transitive closure: smaller_ids <= leaf_id <= greater_id <= greater_ids
                smaller_ids = subsets[leaf_id]
                greater_ids = supersets[greater_id]
                for smaller_id in smaller_ids:
                    supersets[smaller_id].update(greater_ids)
                for greater_id in greater_ids:
                    subsets[greater_id].update(smaller_ids)

        # compute transitive closure of disjoint relation
        disjoints = {leaf.id: leaf.disjoints for leaf in self.__leaves.values()}
        for leaf_id, info in definitions.items():
            for distinct_id in info.get('disjoints', set()):
                # all subsets[leaf_id] are disjoint from all subsets[distinct_id]
                left_ids = subsets[leaf_id]
                right_ids = subsets[distinct_id]
                for left_id in left_ids:
                    disjoints[left_id].update(right_ids)
                for right_id in right_ids:
                    disjoints[right_id].update(left_ids)

    @property
    def empty(self) -> SetExpression:
        return EMPTY_UNION

    @property
    def universe(self) -> SetExpression:
        return UNIVERSAL_UNION

    def parse(self, refs: str, raise_if_not_found: bool = True) -> SetExpression:
        """ Return the set expression corresponding to ``refs``

        :param str refs: comma-separated list of set references
            optionally preceded by ``!`` (negative item). The result is
            an union between positive item who intersect every negative
            group.
            (e.g. ``base.group_user,base.group_portal,!base.group_system``)
        """
        positives: list[Leaf] = []
        negatives: list[Leaf] = []
        for xmlid in refs.split(','):
            if xmlid.startswith('!'):
                negatives.append(~self.__get_leaf(xmlid[1:], raise_if_not_found))
            else:
                positives.append(self.__get_leaf(xmlid, raise_if_not_found))

        if positives:
            return Union(Inter([leaf] + negatives) for leaf in positives)
        else:
            return Union([Inter(negatives)])

    def from_ids(self, ids: Iterable[int], keep_subsets: bool = False) -> SetExpression:
        """ Return the set expression corresponding to given set ids. """
        if keep_subsets:
            ids = set(ids)
            ids = [leaf_id for leaf_id in ids if not any((self.__leaves[leaf_id].subsets - {leaf_id}) & ids)]
        return Union(Inter([self.__leaves[leaf_id]]) for leaf_id in ids)

    def from_key(self, key: str) -> SetExpression:
        """ Return the set expression corresponding to the given key. """
        # union_tuple = tuple(tuple(tuple(leaf_id, negative), ...), ...)
        union_tuple = ast.literal_eval(key)
        return Union([
            Inter([
                ~leaf if negative else leaf
                for leaf_id, negative in inter_tuple
                for leaf in [self.__get_leaf(leaf_id, raise_if_not_found=False)]
            ], optimal=True)
            for inter_tuple in union_tuple
        ], optimal=True)

    def get_id(self, ref: LeafIdType) -> LeafIdType | None:
        """ Return a set id from its reference, or ``None`` if it does not exist. """
        if ref == '*':
            return UNIVERSAL_LEAF.id
        leaf = self.__leaves.get(ref)
        return None if leaf is None else leaf.id

    def __get_leaf(self, ref: str | int, raise_if_not_found: bool = True) -> Leaf:
        """ Return the group object from the string.

        :param str ref: the ref of a leaf
        """
        if ref == '*':
            return UNIVERSAL_LEAF
        if not raise_if_not_found and ref not in self.__leaves:
            return Leaf(UnknownId(ref), ref)
        return self.__leaves[ref]

    def get_superset_ids(self, ids: Iterable[int]) -> list[int]:
        """ Returns the supersets matching the provided list of ids.

        Following example defined in this set definitions constructor::
        The supersets of "Q" (id 3) is "R" and "C" with ids [4, 6]
        """
        return sorted({
            sup_id
            for id_ in ids
            if id_ in self.__leaves
            for sup_id in self.__leaves[id_].supersets
            if sup_id != id_
        })

    def get_subset_ids(self, ids: Iterable[int]) -> list[int]:
        """ Returns the subsets matching the provided list of ids.

        Following example defined in this set definitions constructor::
        The subsets of "Q" (id 3) is "Z" and "N" with ids [1, 2]
        """
        return sorted({
            sub_id
            for id_ in ids
            if id_ in self.__leaves
            for sub_id in self.__leaves[id_].subsets
            if sub_id != id_
        })

    def get_disjoint_ids(self, ids: Iterable[int]) -> list[int]:
        """ Returns the disjoints set matching the provided list of ids.

        Following example defined in this set definitions constructor::
        The disjoint set of "Q" (id 3) is "R\\Q" and "I" with ids [7, 5]
        """
        return sorted({
            disjoint_id
            for id_ in ids
            if id_ in self.__leaves
            for disjoint_id in self.__leaves[id_].disjoints
        })


class SetExpression(ABC):
    """ An object that represents a combination of named sets with union,
    intersection and complement.
    """
    @abstractmethod
    def is_empty(self) -> bool:
        """ Returns whether ``self`` is the empty set, that contains nothing. """
        raise NotImplementedError()

    @abstractmethod
    def is_universal(self) -> bool:
        """ Returns whether ``self`` is the universal set, that contains all possible elements. """
        raise NotImplementedError()

    @abstractmethod
    def invert_intersect(self, factor: SetExpression) -> SetExpression | None:
        """ Performs the inverse operation of intersection (a sort of factorization)
        such that: ``self == result & factor``.
        """
        raise NotImplementedError()

    @abstractmethod
    def matches(self, user_group_ids: Iterable[int]) -> bool:
        """ Return whether the given group ids are included to ``self``. """
        raise NotImplementedError()

    @property
    @abstractmethod
    def key(self) -> str:
        """ Return a unique identifier for the expression. """
        raise NotImplementedError()

    @abstractmethod
    def __and__(self, other: SetExpression) -> SetExpression:
        raise NotImplementedError()

    @abstractmethod
    def __or__(self, other: SetExpression) -> SetExpression:
        raise NotImplementedError()

    @abstractmethod
    def __invert__(self) -> SetExpression:
        raise NotImplementedError()

    @abstractmethod
    def __eq__(self, other) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def __le__(self, other: SetExpression) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def __lt__(self, other: SetExpression) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def __hash__(self):
        raise NotImplementedError()


class Union(SetExpression):
    """ Implementation of a set expression, that represents it as a union of
    intersections of named sets or their complement.
    """
    def __init__(self, inters: Iterable[Inter] = (), optimal=False):
        if inters and not optimal:
            inters = self.__combine((), inters)
        self.__inters = sorted(inters, key=lambda inter: inter.key)
        self.__key = str(tuple(inter.key for inter in self.__inters))
        self.__hash = hash(self.__key)

    @property
    def key(self) -> str:
        return self.__key

    @staticmethod
    def __combine(inters: Iterable[Inter], inters_to_add: Iterable[Inter]) -> list[Inter]:
        """ Combine some existing union of intersections with extra intersections. """
        result = list(inters)

        todo = list(inters_to_add)
        while todo:
            inter_to_add = todo.pop()
            if inter_to_add.is_universal():
                return [UNIVERSAL_INTER]
            if inter_to_add.is_empty():
                continue

            for index, inter in enumerate(result):
                merged = inter._union_merge(inter_to_add)
                if merged is not None:
                    result.pop(index)
                    todo.append(merged)
                    break
            else:
                result.append(inter_to_add)

        return result

    def is_empty(self) -> bool:
        """ Returns whether ``self`` is the empty set, that contains nothing. """
        return not self.__inters

    def is_universal(self) -> bool:
        """ Returns whether ``self`` is the universal set, that contains all possible elements. """
        return any(item.is_universal() for item in self.__inters)

    def invert_intersect(self, factor: SetExpression) -> Union | None:
        """ Performs the inverse operation of intersection (a sort of factorization)
        such that: ``self == result & factor``.
        """
        if factor == self:
            return UNIVERSAL_UNION

        rfactor = ~factor
        if rfactor.is_empty() or rfactor.is_universal():
            return None
        rself = ~self

        assert isinstance(rfactor, Union)
        inters = [inter for inter in rself.__inters if inter not in rfactor.__inters]
        if len(rself.__inters) - len(inters) != len(rfactor.__inters):
            # not possible to invert the intersection
            return None

        rself_value = Union(inters)
        return ~rself_value

    def __and__(self, other: SetExpression) -> Union:
        assert isinstance(other, Union)
        if self.is_universal():
            return other
        if other.is_universal():
            return self
        if self.is_empty() or other.is_empty():
            return EMPTY_UNION
        if self == other:
            return self
        return Union(
            self_inter & other_inter
            for self_inter in self.__inters
            for other_inter in other.__inters
        )

    def __or__(self, other: SetExpression) -> Union:
        assert isinstance(other, Union)
        if self.is_empty():
            return other
        if other.is_empty():
            return self
        if self.is_universal() or other.is_universal():
            return UNIVERSAL_UNION
        if self == other:
            return self
        inters = self.__combine(self.__inters, other.__inters)
        return Union(inters, optimal=True)

    def __invert__(self) -> Union:
        if self.is_empty():
            return UNIVERSAL_UNION
        if self.is_universal():
            return EMPTY_UNION

        # apply De Morgan's laws
        inverses_of_inters = [
            # ~(A & B) = ~A | ~B
            Union(Inter([~leaf]) for leaf in inter.leaves)
            for inter in self.__inters
        ]
        result = inverses_of_inters[0]
        # ~(A | B) = ~A & ~B
        for inverse in inverses_of_inters[1:]:
            result = result & inverse

        return result

    def matches(self, user_group_ids) -> bool:
        if self.is_empty() or not user_group_ids:
            return False
        if self.is_universal():
            return True
        user_group_ids = set(user_group_ids)
        return any(inter.matches(user_group_ids) for inter in self.__inters)

    def __bool__(self):
        raise NotImplementedError()

    def __eq__(self, other) -> bool:
        return isinstance(other, Union) and self.__key == other.__key

    def __le__(self, other: SetExpression) -> bool:
        if not isinstance(other, Union):
            return False
        if self.__key == other.__key:
            return True
        if self.is_universal() or other.is_empty():
            return False
        if other.is_universal() or self.is_empty():
            return True
        return all(
            any(self_inter <= other_inter for other_inter in other.__inters)
            for self_inter in self.__inters
        )

    def __lt__(self, other: SetExpression) -> bool:
        return self != other and self.__le__(other)

    def __str__(self):
        """ Returns an intersection union representation of groups using user-readable references.

            e.g. ('base.group_user' & 'base.group_multi_company') | ('base.group_portal' & ~'base.group_multi_company') | 'base.group_public'
        """
        if self.is_empty():
            return "~*"

        def leaf_to_str(leaf):
            return f"{'~' if leaf.negative else ''}{leaf.ref!r}"

        def inter_to_str(inter, wrapped=False):
            result = " & ".join(leaf_to_str(leaf) for leaf in inter.leaves) or "*"
            return f"({result})" if wrapped and len(inter.leaves) > 1 else result

        wrapped = len(self.__inters) > 1
        return " | ".join(inter_to_str(inter, wrapped) for inter in self.__inters)

    def __repr__(self):
        return repr(self.__str__())

    def __hash__(self):
        return self.__hash


class Inter:
    """ Part of the implementation of a set expression, that represents an
    intersection of named sets or their complement.
    """
    __slots__ = ('key', 'leaves')

    def __init__(self, leaves: Iterable[Leaf] = (), optimal=False):
        if leaves and not optimal:
            leaves = self.__combine((), leaves)
        self.leaves: list[Leaf] = sorted(leaves, key=lambda leaf: leaf.key)
        self.key: tuple[tuple[LeafIdType, bool], ...] = tuple(leaf.key for leaf in self.leaves)

    @staticmethod
    def __combine(leaves: Iterable[Leaf], leaves_to_add: Iterable[Leaf]) -> list[Leaf]:
        """ Combine some existing intersection of leaves with extra leaves. """
        result = list(leaves)
        for leaf_to_add in leaves_to_add:
            for index, leaf in enumerate(result):
                if leaf.isdisjoint(leaf_to_add):  # leaf & leaf_to_add = empty
                    return [EMPTY_LEAF]
                if leaf <= leaf_to_add:  # leaf & leaf_to_add = leaf
                    break
                if leaf_to_add <= leaf:  # leaf & leaf_to_add = leaf_to_add
                    result[index] = leaf_to_add
                    break
            else:
                if not leaf_to_add.is_universal():
                    result.append(leaf_to_add)
        return result

    def is_empty(self) -> bool:
        return any(item.is_empty() for item in self.leaves)

    def is_universal(self) -> bool:
        """ Returns whether ``self`` is the universal set, that contains all possible elements. """
        return not self.leaves

    def matches(self, user_group_ids) -> bool:
        return all(leaf.matches(user_group_ids) for leaf in self.leaves)

    def _union_merge(self, other: Inter) -> Inter | None:
        """ Return the union of ``self`` with another intersection, if it can be
        represented as an intersection. Otherwise return ``None``.
        """
        # the following covers cases like (A & B) | A -> A
        if self.is_universal() or other <= self:
            return self
        if self <= other:
            return other

        # combine complementary parts: (A & ~B) | (A & B) -> A
        if len(self.leaves) == len(other.leaves):
            opposite_index = None
            # we use the property that __leaves are ordered
            for index, self_leaf, other_leaf in zip(range(len(self.leaves)), self.leaves, other.leaves):
                if self_leaf.id != other_leaf.id:
                    return None
                if self_leaf.negative != other_leaf.negative:
                    if opposite_index is not None:
                        return None  # we already have two opposite leaves
                    opposite_index = index
            if opposite_index is not None:
                leaves = list(self.leaves)
                leaves.pop(opposite_index)
                return Inter(leaves, optimal=True)
        return None

    def __and__(self, other: Inter) -> Inter:
        if self.is_empty() or other.is_empty():
            return EMPTY_INTER
        if self.is_universal():
            return other
        if other.is_universal():
            return self
        leaves = self.__combine(self.leaves, other.leaves)
        return Inter(leaves, optimal=True)

    def __eq__(self, other) -> bool:
        return isinstance(other, Inter) and self.key == other.key

    def __le__(self, other: Inter) -> bool:
        return self.key == other.key or all(
            any(self_leaf <= other_leaf for self_leaf in self.leaves)
            for other_leaf in other.leaves
        )

    def __lt__(self, other: Inter) -> bool:
        return self != other and self <= other

    def __hash__(self):
        return hash(self.key)


class Leaf:
    """ Part of the implementation of a set expression, that represents a named
    set or its complement.
    """
    __slots__ = ('disjoints', 'id', 'inverse', 'key', 'negative', 'ref', 'subsets', 'supersets')

    def __init__(self, leaf_id: LeafIdType, ref: str | int | None = None, negative: bool = False):
        self.id = leaf_id
        self.ref = ref or str(leaf_id)
        self.negative = bool(negative)
        self.key: tuple[LeafIdType, bool] = (leaf_id, self.negative)

        self.subsets: set[LeafIdType] = {leaf_id}       # all the leaf ids that are <= self
        self.supersets: set[LeafIdType] = {leaf_id}     # all the leaf ids that are >= self
        self.disjoints: set[LeafIdType] = set()         # all the leaf ids disjoint from self
        self.inverse: Leaf | None = None

    def __invert__(self) -> Leaf:
        if self.inverse is None:
            self.inverse = Leaf(self.id, self.ref, negative=not self.negative)
            self.inverse.inverse = self
            self.inverse.subsets = self.subsets
            self.inverse.supersets = self.supersets
            self.inverse.disjoints = self.disjoints
        return self.inverse

    def is_empty(self) -> bool:
        return self.ref == '*' and self.negative

    def is_universal(self) -> bool:
        return self.ref == '*' and not self.negative

    def isdisjoint(self, other: Leaf) -> bool:
        if self.negative:
            return other <= ~self
        elif other.negative:
            return self <= ~other
        else:
            return self.id in other.disjoints

    def matches(self, user_group_ids: Collection[int]) -> bool:
        return (self.id not in user_group_ids) if self.negative else (self.id in user_group_ids)

    def __eq__(self, other) -> bool:
        return isinstance(other, Leaf) and self.key == other.key

    def __le__(self, other: Leaf) -> bool:
        if self.is_empty() or other.is_universal():
            return True
        elif self.is_universal() or other.is_empty():
            return False
        elif self.negative:
            return other.negative and ~other <= ~self
        elif other.negative:
            return self.id in other.disjoints
        else:
            return self.id in other.subsets

    def __lt__(self, other: Leaf) -> bool:
        return self != other and self <= other

    def __hash__(self):
        return hash(self.key)


class UnknownId(str):
    """ Special id object for unknown leaves.  It behaves as being strictly
    greater than any other kind of id.
    """
    __slots__ = ()

    def __lt__(self, other) -> bool:
        if isinstance(other, UnknownId):
            return super().__lt__(other)
        return False

    def __gt__(self, other) -> bool:
        if isinstance(other, UnknownId):
            return super().__gt__(other)
        return True


LeafIdType = int | typing.Literal["*"] | UnknownId

# constants
UNIVERSAL_LEAF = Leaf('*')
EMPTY_LEAF = ~UNIVERSAL_LEAF

EMPTY_INTER = Inter([EMPTY_LEAF])
UNIVERSAL_INTER = Inter()

EMPTY_UNION = Union()
UNIVERSAL_UNION = Union([UNIVERSAL_INTER])
