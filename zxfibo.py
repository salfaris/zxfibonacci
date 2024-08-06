import math

from fractions import Fraction
import pyzx as zx

import qiskit

BinarySequence = str
Count = int
Result = dict[BinarySequence, Count]


def zxfibo(n: int):
    return ZXFibo(n_qubits=n).number(tau=0)


class ZXFibo:
    def __init__(self, n_qubits: int):
        if not n_qubits > 1:
            raise ValueError("n_qubits has to be > 1.")
        self.n_qubits = n_qubits
        return

    def pyzx_circuit(self):
        circ = zx.Circuit(self.n_qubits)
        # For each qubit, add an X(\pi/2) gate.
        for qubit in range(self.n_qubits):
            circ.add_gate("XPhase", qubit, Fraction(1, 2))
        # For each qubit n > 1, add a controlled X(\pi/2) gate.
        for qubit in range(self.n_qubits - 1):
            _add_cx_alpha_gate(circ, Fraction(-1, 2), qubit, qubit + 1)
        return circ

    def ibm_circuit(self):
        return _pyzx_to_qiskit(self.pyzx_circuit())

    def eval(self):
        backend = qiskit.Aer.get_backend("qasm_simulator")
        shots = 1000
        config = {"backend": backend, "shots": shots}
        count = _run_circuit(self.ibm_circuit(), backend=backend, shots=shots)
        return count, config

    def number(self, tau: float = 0.05):
        count, config = self.eval()
        proba = {k: v / config["shots"] for k, v in count.items()}
        fibo_n = 0
        for v in proba.values():
            if v > tau:
                fibo_n += 1
        return fibo_n


def _run_circuit(
    circ: qiskit.QuantumCircuit,
    backend: qiskit.providers.Backend,
    shots: int = 1000,
) -> Result:
    job = qiskit.execute(circ, backend, shots=shots)
    result = job.result()
    counts = result.get_counts()
    return counts


def _add_cx_alpha_gate(
    circuit: zx.Circuit, alpha: Fraction | int, control: int, target: int
) -> zx.Circuit:
    """Adds a CX(alpha) gate"""
    circuit.add_gate("HAD", target)
    circuit.add_gate("ZPhase", control, phase=alpha * Fraction(1, 2))
    circuit.add_gate("ZPhase", target, phase=alpha * Fraction(1, 2))
    circuit.add_gate("CNOT", control, target)
    circuit.add_gate("ZPhase", target, phase=alpha * Fraction(-1, 2))
    circuit.add_gate("CNOT", control, target)
    circuit.add_gate("HAD", target)
    return circuit


def _pyzx_to_qiskit(circ: zx.Circuit) -> qiskit.QuantumCircuit:
    """Converts a PyZX circuit into a Qiskit circuit.

    I think this was Aleks/John's code.
    """
    circ = circ.to_basic_gates()
    q = circ.qubits
    ibm_circ = qiskit.QuantumCircuit(q, q)
    for gate in circ.gates:
        if isinstance(gate, zx.gates.CNOT):
            ibm_circ.cnot(gate.control, gate.target)
        elif isinstance(gate, zx.gates.CZ):
            ibm_circ.cz(gate.control, gate.target)
        elif isinstance(gate, zx.gates.HAD):
            ibm_circ.h(gate.target)
        elif isinstance(gate, zx.gates.ZPhase):
            ibm_circ.rz(math.pi * gate.phase, gate.target)
        elif isinstance(gate, zx.gates.XPhase):
            ibm_circ.rx(math.pi * gate.phase, gate.target)
    ibm_circ.measure(range(q), range(q))
    return ibm_circ
