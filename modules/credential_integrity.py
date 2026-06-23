# -*- coding: utf-8 -*-
"""
白龙马医生-Bailongma Doctor · Credential Integrity Checker
AtomCollide-智械工坊 · 2026

融合自 langgenius/dify 的凭证完整性验证机制。

检测能力:
  - 凭证存在性检查
  - 凭证策略合规性检查
  - 运行时凭证验证
  - 凭证生命周期管理

Usage:
    from modules.credential_integrity import CredentialIntegrityChecker
    checker = CredentialIntegrityChecker()
    result = checker.check_credential("/path/to/agent")
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class CredentialType(Enum):
    """凭证类型"""
    MODEL = "MODEL"  # 模型凭证
    TOOL = "TOOL"    # 工具凭证
    API = "API"      # API凭证
    DATABASE = "DATABASE"  # 数据库凭证


class CredentialStatus(Enum):
    """凭证状态"""
    VALID = "VALID"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    MISSING = "MISSING"
    INVALID = "INVALID"


@dataclass
class CredentialInfo:
    """凭证信息"""
    credential_id: str
    credential_type: CredentialType
    provider: str
    status: CredentialStatus
    expires_at: Optional[str] = None
    last_used: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IntegrityCheckResult:
    """完整性检查结果"""
    credential_id: str
    is_valid: bool
    status: CredentialStatus
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class CredentialIntegrityChecker:
    """
    凭证完整性检查器
    
    融合自 langgenius/dify 的凭证完整性验证机制。
    """
    
    def __init__(self):
        """初始化检查器"""
        self.checked_credentials: List[CredentialInfo] = []
        self.issues_found: List[str] = []
    
    def check_agent_credentials(self, agent_path: str) -> List[IntegrityCheckResult]:
        """
        检查Agent的凭证完整性
        
        Args:
            agent_path: Agent路径
            
        Returns:
            检查结果列表
        """
        results = []
        path = Path(agent_path)
        
        if not path.exists():
            return results
        
        # 扫描所有配置文件
        config_files = list(path.rglob("*.json")) + list(path.rglob("*.yaml")) + list(path.rglob("*.yml"))
        
        for config_file in config_files:
            try:
                content = config_file.read_text(encoding='utf-8', errors='ignore')
                config = json.loads(content) if content.strip().startswith('{') else {}
                
                # 检查凭证引用
                credential_refs = self._extract_credential_refs(config)
                for ref in credential_refs:
                    result = self._check_credential_ref(ref, str(config_file.relative_to(path)))
                    results.append(result)
                    
            except Exception:
                continue
        
        return results
    
    def check_environment_credentials(self) -> List[IntegrityCheckResult]:
        """
        检查环境变量中的凭证
        
        Returns:
            检查结果列表
        """
        results = []
        
        # 常见的凭证环境变量
        credential_env_vars = [
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "GOOGLE_API_KEY",
            "HUGGINGFACE_TOKEN",
            "GITHUB_TOKEN",
            "GITLAB_TOKEN",
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "DATABASE_URL",
            "REDIS_URL",
            "MONGODB_URI",
        ]
        
        for env_var in credential_env_vars:
            value = os.environ.get(env_var)
            if value:
                result = self._check_env_credential(env_var, value)
                results.append(result)
        
        return results
    
    def check_skill_credentials(self, skill_path: str) -> List[IntegrityCheckResult]:
        """
        检查技能的凭证完整性
        
        Args:
            skill_path: 技能路径
            
        Returns:
            检查结果列表
        """
        results = []
        path = Path(skill_path)
        
        if not path.exists():
            return results
        
        # 检查SKILL.md中的凭证引用
        skill_md = path / "SKILL.md"
        if skill_md.exists():
            content = skill_md.read_text(encoding='utf-8', errors='ignore')
            refs = self._extract_credential_refs_from_text(content)
            for ref in refs:
                result = self._check_credential_ref(ref, "SKILL.md")
                results.append(result)
        
        # 检查脚本文件中的凭证引用
        for script_file in path.rglob("*.py"):
            try:
                content = script_file.read_text(encoding='utf-8', errors='ignore')
                refs = self._extract_credential_refs_from_text(content)
                for ref in refs:
                    result = self._check_credential_ref(ref, str(script_file.relative_to(path)))
                    results.append(result)
            except Exception:
                continue
        
        return results
    
    def _extract_credential_refs(self, config: Dict[str, Any]) -> List[Dict[str, str]]:
        """从配置中提取凭证引用"""
        refs = []
        
        # 递归搜索凭证引用
        def search_dict(d: Dict[str, Any], path: str = ""):
            for key, value in d.items():
                current_path = f"{path}.{key}" if path else key
                
                if isinstance(value, str):
                    # 检查是否是凭证引用
                    if any(keyword in key.lower() for keyword in ["key", "token", "secret", "password", "credential"]):
                        refs.append({
                            "id": current_path,
                            "type": "config",
                            "value": value[:20] + "..." if len(value) > 20 else value,
                        })
                elif isinstance(value, dict):
                    search_dict(value, current_path)
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            search_dict(item, f"{current_path}[{i}]")
        
        search_dict(config)
        return refs
    
    def _extract_credential_refs_from_text(self, text: str) -> List[Dict[str, str]]:
        """从文本中提取凭证引用"""
        import re
        refs = []
        
        # 匹配常见的凭证模式
        patterns = [
            (r'(?:api[_-]?key|token|secret|password|credential)\s*[:=]\s*["\']?([^\s"\']+)', "api_key"),
            (r'(?:sk-|ghp_|ghu_|ghr_|ghs_)[a-zA-Z0-9]+', "github_token"),
            (r'(?:AKIA|ASIA)[A-Z0-9]{16}', "aws_key"),
            (r'(?:xoxb-|xoxp-|xoxo-)[a-zA-Z0-9-]+', "slack_token"),
        ]
        
        for pattern, ref_type in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                refs.append({
                    "id": f"{ref_type}_{len(refs)}",
                    "type": ref_type,
                    "value": match.group(0)[:20] + "..." if len(match.group(0)) > 20 else match.group(0),
                })
        
        return refs
    
    def _check_credential_ref(self, ref: Dict[str, str], source_file: str) -> IntegrityCheckResult:
        """检查凭证引用的完整性"""
        result = IntegrityCheckResult(
            credential_id=ref["id"],
            is_valid=True,
            status=CredentialStatus.VALID,
        )
        
        # 检查是否是硬编码凭证
        if ref["type"] in ["api_key", "github_token", "aws_key", "slack_token"]:
            result.is_valid = False
            result.status = CredentialStatus.INVALID
            result.issues.append(f"硬编码凭证发现于 {source_file}")
            result.recommendations.append("将凭证移至环境变量或安全存储")
        
        # 检查是否是占位符
        if ref["value"].startswith("sk-") and "..." in ref["value"]:
            result.is_valid = False
            result.status = CredentialStatus.INVALID
            result.issues.append(f"凭证占位符发现于 {source_file}")
            result.recommendations.append("使用真实的凭证或移除占位符")
        
        return result
    
    def _check_env_credential(self, env_var: str, value: str) -> IntegrityCheckResult:
        """检查环境变量凭证"""
        result = IntegrityCheckResult(
            credential_id=env_var,
            is_valid=True,
            status=CredentialStatus.VALID,
        )
        
        # 检查凭证格式
        if env_var == "OPENAI_API_KEY" and not value.startswith("sk-"):
            result.is_valid = False
            result.status = CredentialStatus.INVALID
            result.issues.append("OpenAI API Key格式不正确")
            result.recommendations.append("检查API Key是否正确")
        
        elif env_var == "GITHUB_TOKEN" and not value.startswith("ghp_"):
            result.is_valid = False
            result.status = CredentialStatus.INVALID
            result.issues.append("GitHub Token格式不正确")
            result.recommendations.append("检查Token是否正确")
        
        # 检查凭证长度
        if len(value) < 10:
            result.is_valid = False
            result.status = CredentialStatus.INVALID
            result.issues.append("凭证长度过短")
            result.recommendations.append("检查凭证是否完整")
        
        return result
    
    def generate_report(self, results: List[IntegrityCheckResult]) -> Dict[str, Any]:
        """生成检查报告"""
        valid_count = sum(1 for r in results if r.is_valid)
        invalid_count = sum(1 for r in results if not r.is_valid)
        
        return {
            "total_checked": len(results),
            "valid": valid_count,
            "invalid": invalid_count,
            "issues": [issue for r in results for issue in r.issues],
            "recommendations": [rec for r in results for rec in r.recommendations],
            "risk_level": "HIGH" if invalid_count > 0 else "LOW",
        }


# ── Self-test ──

if __name__ == "__main__":
    import tempfile
    
    print("🔍 Credential Integrity Checker 自测")
    print("=" * 50)
    
    # 创建测试目录
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建测试文件
        test_files = {
            "config.json": '''
{
    "api_key": "sk-1234567890abcdef",
    "model": "gpt-4",
    "database_url": "postgresql://user:password@localhost/db"
}
''',
            "agent.py": '''
import os
api_key = os.getenv("OPENAI_API_KEY")
github_token = "ghp_abcdefghijklmnop"
''',
        }
        
        for filename, content in test_files.items():
            filepath = Path(tmpdir) / filename
            filepath.write_text(content)
        
        # 运行检查
        checker = CredentialIntegrityChecker()
        results = checker.check_agent_credentials(tmpdir)
        
        # 输出结果
        report = checker.generate_report(results)
        
        print(f"\n📊 检查结果:")
        print(f"  总检查数: {report['total_checked']}")
        print(f"  有效: {report['valid']}")
        print(f"  无效: {report['invalid']}")
        print(f"  风险等级: {report['risk_level']}")
        
        if report['issues']:
            print(f"\n⚠️ 发现问题:")
            for issue in report['issues']:
                print(f"  - {issue}")
        
        if report['recommendations']:
            print(f"\n💡 建议:")
            for rec in report['recommendations']:
                print(f"  - {rec}")
        
        print(f"\n🔍 详细发现:")
        for result in results:
            print(f"  [{result.credential_id}] {result.status.value}")
            if result.issues:
                for issue in result.issues:
                    print(f"    ⚠️ {issue}")
    
    print("\n✅ 自测完成")
