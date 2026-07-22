"""Tests for p1-2: tool provider contracts (dify-inspired)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from tool_contract import (
    tool_contract,
    validate_input,
    list_contracts,
    ContractViolation,
    CONTRACT_REGISTRY,
    ToolContract,
)


@pytest.fixture(autouse=True)
def clean_registry():
    """Ensure a clean registry for each test."""
    saved = dict(CONTRACT_REGISTRY)
    CONTRACT_REGISTRY.clear()
    yield
    CONTRACT_REGISTRY.clear()
    CONTRACT_REGISTRY.update(saved)


class TestToolContractDecorator:

    def test_registers_in_registry(self):
        @tool_contract(name="test_echo", inputs={"msg": str}, risk="safe")
        def echo(msg: str) -> dict:
            return {"result": msg}

        assert "test_echo" in CONTRACT_REGISTRY
        assert CONTRACT_REGISTRY["test_echo"].risk == "safe"

    def test_valid_call_passes(self):
        @tool_contract(name="test_add", inputs={"a": int, "b": int})
        def add(a: int, b: int) -> dict:
            return {"sum": a + b}

        result = add(a=1, b=2)
        assert result == {"sum": 3}

    def test_wrong_type_raises_violation(self):
        @tool_contract(name="test_strict", inputs={"count": int})
        def strict(count: int) -> dict:
            return {"count": count}

        with pytest.raises(ContractViolation) as exc_info:
            strict(count="not_an_int")
        assert "count" in str(exc_info.value)

    def test_requires_confirmation(self):
        @tool_contract(name="test_danger", inputs={}, risk="dangerous", requires_confirmation=True)
        def danger() -> dict:
            return {"done": True}

        with pytest.raises(ContractViolation) as exc_info:
            danger()
        assert "confirm=True" in str(exc_info.value)

        result = danger(confirm=True)
        assert result == {"done": True}

    def test_output_validation(self):
        @tool_contract(
            name="test_output",
            outputs={"status": str, "code": int},
        )
        def good_output() -> dict:
            return {"status": "ok", "code": 0}

        assert good_output() == {"status": "ok", "code": 0}

    def test_output_missing_field_raises(self):
        @tool_contract(
            name="test_bad_output",
            outputs={"status": str, "code": int},
        )
        def bad_output() -> dict:
            return {"status": "ok"}  # missing "code"

        with pytest.raises(ContractViolation) as exc_info:
            bad_output()
        assert "code" in str(exc_info.value)


class TestValidateInput:

    def test_unknown_tool_returns_error(self):
        errors = validate_input("nonexistent_tool", {})
        assert any("Unknown tool" in e for e in errors)

    def test_valid_params_empty_errors(self):
        @tool_contract(name="test_validate", inputs={"path": str})
        def check(path: str) -> dict:
            return {"path": path}

        errors = validate_input("test_validate", {"path": "/tmp"})
        assert errors == []

    def test_wrong_type_detected(self):
        @tool_contract(name="test_validate2", inputs={"timeout": int})
        def check(timeout: int) -> dict:
            return {"timeout": timeout}

        errors = validate_input("test_validate2", {"timeout": "slow"})
        assert len(errors) == 1
        assert "timeout" in errors[0]


class TestListContracts:

    def test_returns_registered_contracts(self):
        @tool_contract(name="alpha", description="Alpha tool")
        def alpha() -> dict:
            return {}

        @tool_contract(name="beta", description="Beta tool")
        def beta() -> dict:
            return {}

        contracts = list_contracts()
        assert "alpha" in contracts
        assert "beta" in contracts
        assert contracts["alpha"].description == "Alpha tool"
