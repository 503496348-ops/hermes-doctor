# -*- coding: utf-8 -*-
"""
Tool Provider Contracts — dify-inspired declarative tool interface validation.

Decorators for diagnostic/prescription tools to declare their input schema,
output schema, risk level, and required credentials. Runtime validates inputs
before execution and provides clear error messages on contract violations.

Usage:
    from tool_contract import tool_contract, validate_input, CONTRACT_REGISTRY

    @tool_contract(
        name="check_feishu_bot",
        inputs={"chat_id": str, "timeout": int},
        outputs={"status": str, "details": str},
        risk="safe",
    )
    def check_feishu_bot(chat_id: str, timeout: int = 5) -> dict:
        ...

    # Validate inputs before calling
    errors = validate_input("check_feishu_bot", {"chat_id": "oc_xxx", "timeout": 3})
    if errors:
        raise ContractViolation(errors)
"""
from __future__ import annotations

import functools
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type


CONTRACT_REGISTRY: Dict[str, "ToolContract"] = {}


@dataclass(frozen=True)
class ToolContract:
    """Declarative contract for a diagnostic/prescription tool."""
    name: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    risk: str = "safe"  # safe / caution / dangerous
    requires_confirmation: bool = False
    description: str = ""


class ContractViolation(Exception):
    """Structured error for contract violations."""
    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__("; ".join(errors))

    def __bool__(self) -> bool:
        return len(self.errors) > 0


def tool_contract(
    name: str,
    inputs: Dict[str, Any] | None = None,
    outputs: Dict[str, Any] | None = None,
    risk: str = "safe",
    requires_confirmation: bool = False,
    description: str = "",
) -> Callable:
    """
    Decorator: register a tool's contract and validate inputs at call time.

    - name: unique tool identifier
    - inputs: {param_name: expected_type} — validates kwargs before execution
    - outputs: {field_name: expected_type} — validates return dict after execution
    - risk: "safe" | "caution" | "dangerous"
    - requires_confirmation: if True, caller must pass confirm=True
    """
    contract = ToolContract(
        name=name,
        inputs=inputs or {},
        outputs=outputs or {},
        risk=risk,
        requires_confirmation=requires_confirmation,
        description=description,
    )

    def decorator(func: Callable) -> Callable:
        CONTRACT_REGISTRY[name] = contract

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Input validation
            errors = _validate_inputs(contract, kwargs)
            if contract.requires_confirmation and not kwargs.pop("confirm", False):
                errors.append(f"Tool '{name}' requires explicit confirm=True (risk={risk})")
            if errors:
                raise ContractViolation(errors)

            result = func(*args, **kwargs)

            # Output validation (only for dict returns)
            if isinstance(result, dict) and contract.outputs:
                out_errors = _validate_outputs(contract, result)
                if out_errors:
                    raise ContractViolation([f"Output: {e}" for e in out_errors])

            return result

        wrapper._contract = contract  # type: ignore[attr-defined]
        return wrapper

    return decorator


def validate_input(tool_name: str, params: Dict[str, Any]) -> List[str]:
    """
    Validate parameters against a registered tool's contract.
    Returns list of error strings (empty = valid).
    """
    contract = CONTRACT_REGISTRY.get(tool_name)
    if not contract:
        return [f"Unknown tool: '{tool_name}' — no contract registered"]
    return _validate_inputs(contract, params)


def list_contracts() -> Dict[str, ToolContract]:
    """Return all registered tool contracts."""
    return dict(CONTRACT_REGISTRY)


def _validate_inputs(contract: ToolContract, params: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    for param_name, expected_type in contract.inputs.items():
        if param_name not in params:
            # Check if it has a default (handled by Python, not our concern)
            continue
        value = params[param_name]
        if not isinstance(value, expected_type):
            errors.append(
                f"Parameter '{param_name}': expected {expected_type.__name__}, "
                f"got {type(value).__name__}"
            )
    return errors


def _validate_outputs(contract: ToolContract, result: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    for field_name, expected_type in contract.outputs.items():
        if field_name not in result:
            errors.append(f"Missing output field: '{field_name}'")
            continue
        value = result[field_name]
        if not isinstance(value, expected_type):
            errors.append(
                f"Output '{field_name}': expected {expected_type.__name__}, "
                f"got {type(value).__name__}"
            )
    return errors
