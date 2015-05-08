#!/usr/bin/env python
"""fault_tree_generator.py

A script to generate a fault tree of various complexities. The generated
fault tree is put into XML file with OpenPSA MEF ready for analysis.
This script should help create complex fault trees to test analysis tools.
"""
from __future__ import print_function

import Queue
import random

import argparse as ap

class Node(object):
    """Representation of a base class for a node in a fault tree.

    Attributes:
        name: A specific name that identifies this node.
        parents: A set of parents of this node.
    """
    def __init__(self, name=""):
        self.name = name
        self.parents = set()

class Gate(Node):
    """Representation of a gate of a fault tree.

        Names are assigned sequentially starting from G0.
        G0 is assumed to be the root gate.

    Attributes:
        num_gates: Total number of gates created.
        p_children: Children of this gate that are primary events.
        g_children: Children of this gate that are gates.
        gate: Type of the gate.
        ancestors: Ancestor gates of this gate.
    """
    num_gates = 0  # To keep track of gates and to name them
    def __init__(self):
        super(Gate, self).__init__("G" + str(Gate.num_gates))
        Gate.num_gates += 1  # Post-decrement to account for the root gate
        self.p_children = set()  # Children that are primary events
        self.g_children = set()  # Children that are gates
        self.ancestors = set()
        self.gate = ""  # Type of a gate

class PrimaryEvent(Node):
    """Representation of a primary event in a fault tree.

        Names are assigned sequentially starting from E1.

    Attributes:
        num_prime: Total number of primary events created.
        prob: Probability of failure of this primary event.
    """
    num_primary = 0  # Number of primary events
    def __init__(self):
        PrimaryEvent.num_primary += 1
        super(PrimaryEvent, self).__init__("E" + str(PrimaryEvent.num_primary))
        self.prob = 0

def generate_fault_tree(args):
    """Generates a fault tree of specified complexity from command-line
    arguments.

    Args:
        args: Configurations for fault tree construction.

    Returns:
        Top event and a container with primary events.
    """
    # Container for created primary events.
    primary_events = []

    # Supported types of gates.
    gate_types = ["or", "and"]

    # Minimum number of children per intermediate event.
    min_children = 2

    # Maximum number of children.
    max_children = args.nchildren * 2 - min_children

    # Tree generation.
    # Start with a top event.
    top_event = Gate()
    top_event.name = args.root
    top_event.gate = random.choice(gate_types)
    child_size = random.randint(min_children, max_children)

    # Configuring child size for the top event.
    if args.ctop:
        child_size = args.ctop
    elif child_size < args.ptop:
        child_size = args.ptop

    # Container for not yet initialized intermediate events.
    gates_queue = Queue.Queue()

    def create_gate(parent):
        """Handles proper creation of gates.

        The new gate is created with type, parent, and ancestor information.
        The type is chosen randomly.

        Args:
            parent: The parent gate for the new gate.

        Returns:
            A newly created gate.
        """
        gate = Gate()
        gate.gate = random.choice(gate_types)
        parent.g_children.add(gate)
        gate.parents.add(parent)
        gate.ancestors.add(gate)
        gate.ancestors.update(parent.ancestors)
        return gate

    def create_primary(parent):
        """Handles proper creation of primary events

        The new primary event is given a random probability. The parent and
        child information is updated.

        Args:
            parent: The parent gate of the new primary event.

        Returns:
            A newly created primary event.
        """
        primary_event = PrimaryEvent()
        primary_event.prob = random.uniform(args.minprob, args.maxprob)
        parent.p_children.add(primary_event)
        primary_event.parents.add(parent)
        return primary_event


    # Initialize the top root node.
    while (len(top_event.p_children) + len(top_event.g_children)) < child_size:
        while len(top_event.p_children) < args.ptop:
            primary_events.append(create_primary(top_event))
        gates_queue.put(create_gate(top_event))

    # Initialize intermediate events.
    while not gates_queue.empty():
        # Get the intermediate event to intialize
        init_inter = gates_queue.get()

        # Sample children size
        child_size = random.randint(min_children, max_children)

        while (len(init_inter.p_children) +
               len(init_inter.g_children)) < child_size:
            # Case when the number of primary events is already satisfied
            if len(primary_events) == args.nprimary:
                # Reuse already initialized events only
                init_inter.p_children.add(random.choice(primary_events))
                continue

            # Sample inter events vs. primary events
            s_ratio = random.random()
            if s_ratio < (1.0/(1 + args.ratio)):
                gates_queue.put(create_gate(init_inter))
            else:
                # Create a primary event
                # Sample reuse_p
                s_reuse = random.random()
                if s_reuse < args.reuse_p and not primary_events:
                    # Reuse an already initialized primary event
                    init_inter.p_children.add(random.choice(primary_events))
                else:
                    primary_events.append(create_primary(init_inter))

            # Corner case when not enough new primary events initialized, but
            # ther are no more intemediate events due to low ratio.
            if gates_queue.empty() and (len(primary_events) < args.nprimary):
                # Initialize one more intermediate event.
                # This is a naive implementation, so
                # there might be another algorithm in future.
                gates_queue.put(create_gate(init_inter))

    return top_event, primary_events

def write_info(args):
    """Writes the information about the setup and generated fault tree.

    This function uses the output destination from the arguments.

    Args:
        args: Command-line configurations.
    """
    t_file = open(args.out, "w")
    t_file.write("<?xml version=\"1.0\"?>\n")
    t_file.write(
            "<!--\nThis is an autogenerated fault tree description\n"
            "with the following parameters:\n\n"
            "The seed of a random number generator: " + str(args.seed) + "\n"
            "The number of unique primary events: " + str(args.nprimary) + "\n"
            "The average number of children per gate: " +
            str(args.nchildren) + "\n"
            "Primary events to gates ratio per new node: " +
            str(args.ratio) + "\n"
            "Approximate percentage of repeated primary events in the tree: " +
            str(args.reuse_p) + "\n"
            "Approximate percentage of repeated gates in the tree: " +
            str(args.reuse_g) + "\n"
            "Maximum probability for primary events: " +
            str(args.maxprob) + "\n"
            "Minimum probability for primary events: " +
            str(args.minprob) + "\n"
            "Minimal number of primary events for the root node: " +
            str(args.ptop) + "\n"
            "Name of a file to write the fault tree: " + str(args.out) + "\n"
            "-->\n"
            )
    t_file.write(
            "<!--\nThe generated fault tree has the following metrics:\n\n"
            "The number of primary events: " +
            str(PrimaryEvent.num_primary) + "\n"
            "The number of gates: " + str(Gate.num_gates) + "\n"
            "Primary events to gates ratio: " +
            str(PrimaryEvent.num_primary * 1.0 / Gate.num_gates) + "\n"
            "-->\n\n"
            )

def write_model_data(t_file, primary_events):
    """Appends model data with primary event descriptions.

    Args:
        t_file: The output stream.
        primary_events: A set of primary events.
    """
    # Print probabilities of primary events
    t_file.write("<model-data>\n")
    for p in primary_events:
        t_file.write("<define-basic-event name=\"" + p.name + "\">\n"
                     "<float value=\"" + str(p.prob) + "\"/>\n"
                     "</define-basic-event>\n")

    t_file.write("</model-data>\n")

def write_results(args, top_event, primary_events):
    """Writes results of a generated fault tree.

    Writes the information about the fault tree in an XML file.
    The fault tree is printed breadth-first.
    The output XML file is not formatted for human readability.

    Args:
        args: Configurations of this fault tree generation process.
        top_event: Top gate of the generated fault tree.
        primary_events: A set of primary events of the fault tree.
    """
    # Plane text is used instead of any XML tools for performance reasons.
    write_info(args)
    t_file = open(args.out, "a")

    t_file.write("<opsa-mef>\n")
    t_file.write("<define-fault-tree name=\"%s\">\n" % args.ft_name)

    # Container for not yet initialized intermediate events.
    gates_queue = Queue.Queue()

    def write_node(inter_event, o_file):
        """Print children for the intermediate event.
        Note that it also updates the queue for intermediate events.
        """

        o_file.write("<define-gate name=\"" + inter_event.name + "\">\n")
        o_file.write("<" + inter_event.gate + ">\n")
        # Print primary events
        for p in inter_event.p_children:
            o_file.write("<basic-event name=\"" + p.name + "\"/>\n")

        # Print intermediate events
        for i in inter_event.g_children:
            o_file.write("<gate name=\"" + i.name + "\"/>\n")
            # Update the queue
            gates_queue.put(i)

        o_file.write("</" + inter_event.gate + ">\n")
        o_file.write("</define-gate>\n")

    # Write top event and update queue of intermediate events
    # Write top event and update queue of intermediate events
    write_node(top_event, t_file)

    # Proceed with intermediate events
    while not gates_queue.empty():
        i_event = gates_queue.get()
        write_node(i_event, t_file)

    t_file.write("</define-fault-tree>\n")

    write_model_data(t_file, primary_events)

    t_file.write("</opsa-mef>")
    t_file.close()

def check_if_positive(desc, val):
    """Verifies that the value is potive or zero for the supplied argument.

    Args:
        desc: The description of the argument from the command-line.
        val: The value of the argument.

    Raises:
        ArgumentTypeError: The value is negative.
    """
    if val < 0:
        raise ap.ArgumentTypeError(desc + " is negative")

def check_if_less(desc, val, ref):
    """Verifies that the value is less than some reference for
    the supplied argument.

    Args:
        desc: The description of the argument from the command-line.
        val: The value of the argument.
        ref: The reference value.

    Raises:
        ArgumentTypeError: The value is more than the reference.
    """
    if val > ref:
        raise ap.ArgumentTypeError(desc + " is more than " + str(ref))

def main():
    """Verifies arguments and calls fault tree generator functions.

    Raises:
        ArgumentTypeError: There are problemns with the arguments.
    """
    description = "A script to create a fault tree of an arbitrary size and"\
                  " complexity."

    parser = ap.ArgumentParser(description=description)

    ft_name = "the name for the fault tree"
    parser.add_argument("--ft-name", type=str, help=ft_name,
                        default="Autogenerated")

    root = "the name for the root gate"
    parser.add_argument("--root", type=str, help=root, default="root")

    seed = "the seed of a random number generator"
    parser.add_argument("--seed", type=int, help=seed, default=123)

    nprimary = "the number of unique primary events"
    parser.add_argument("-p", "--nprimary", type=int, help=nprimary,
                        default=10)

    nchildren = "the average number of children per gate"
    parser.add_argument("-c", "--nchildren", type=int, help=nchildren,
                        default=3)

    ratio = "primary events to gates ratio per a new gate"
    parser.add_argument("--ratio", type=float, help=ratio, default=2)

    reuse_p = "approximate percentage of repeated primary events in the tree"
    parser.add_argument("--reuse-p", type=float, help=reuse_p, default=0.1)

    reuse_g = "approximate percentage of repeated gates in the tree"
    parser.add_argument("--reuse-g", type=float, help=reuse_g, default=0.1)

    maxprob = "maximum probability for primary events"
    parser.add_argument("--maxprob", type=float, help=maxprob,
                        default=0.1)

    minprob = "minimum probability for primary events"
    parser.add_argument("--minprob", type=float, help=minprob,
                        default=0.001)

    ptop = "minimal number of primary events for a root node"
    parser.add_argument("--ptop", type=int, help=ptop,
                        default=0)

    ctop = "minimal number of children for a root node"
    parser.add_argument("--ctop", type=int, help=ctop,
                        default=0)

    out = "output file to write the generated fault tree"
    parser.add_argument("-o", "--out", help=out, default="fault_tree.xml")

    args = parser.parse_args()

    # Check for validity of arguments
    check_if_positive(ctop, args.ctop)
    check_if_positive(ptop, args.ptop)
    check_if_positive(ratio, args.ratio)
    check_if_positive(nchildren, args.nchildren)
    check_if_positive(nprimary, args.nprimary)
    check_if_positive(minprob, args.minprob)
    check_if_positive(maxprob, args.maxprob)
    check_if_positive(reuse_p, args.reuse_p)
    check_if_positive(reuse_g, args.reuse_g)

    check_if_less(reuse_p, args.reuse_p, 0.9)
    check_if_less(reuse_g, args.reuse_p, 0.9)
    check_if_less(maxprob, args.maxprob, 1)
    check_if_less(minprob, args.minprob, 1)

    if args.maxprob < args.minprob:
        raise ap.ArgumentTypeError("Max probability < Min probability")

    if args.ptop > args.nprimary:
        raise ap.ArgumentTypeError("ptop > # of total primary events")

    if args.ptop > args.ctop:
        raise ap.ArgumentTypeError("ptop > # of children for top")

    # Set the seed for this tree generator.
    random.seed(args.seed)

    top_event, primary_events = generate_fault_tree(args)

    # Write output files
    write_results(args, top_event, primary_events)


if __name__ == "__main__":
    try:
        main()
    except ap.ArgumentTypeError as error:
        print("Argument Error:")
        print(error)
