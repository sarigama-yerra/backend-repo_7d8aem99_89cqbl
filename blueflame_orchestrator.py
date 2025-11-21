import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple

PROMPTS_PATH = os.path.join(os.getcwd(), 'blueflame_prompts.json')

class OrchestratorError(Exception):
    pass

class BlueflameOrchestrator:
    """
    Minimal orchestrator that loads templated prompts and exposes call sites
    where a real Blue Flame API/client can be integrated. In MOCK_MODE we do
    not call any external services; instead, we simply return stub payloads
    and respect retry/backoff fields from prompt metadata.
    """
    def __init__(self, mock: bool = True):
        self.mock = mock
        with open(PROMPTS_PATH, 'r', encoding='utf-8') as f:
            self.prompts = json.load(f)

    def _render(self, template: str, ctx: Dict[str, Any]) -> str:
        out = template
        # Very lightweight rendering: replace {{key}} with str(value)
        for k, v in ctx.items():
            out = out.replace('{{'+k+'}}', str(v))
        return out

    def call(self, name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        if name not in self.prompts:
            raise OrchestratorError(f'Unknown prompt: {name}')
        spec = self.prompts[name]
        prompt = self._render(spec.get('prompt', ''), context)
        retry = spec.get('retry', {"max": 1, "backoff_ms": 500})
        attempts = 0
        last_err: Optional[Exception] = None
        while attempts < retry.get('max', 1):
            try:
                if self.mock:
                    # Simulate latency and return stub response shaped like spec["returns"]
                    time.sleep(retry.get('backoff_ms', 500)/1000.0)
                    return spec.get('returns', {})
                else:
                    # Integration point: call Blue Flame API with `prompt`
                    # Example:
                    # response = blueflame_client.generate(prompt)
                    # return response
                    raise NotImplementedError('Real API integration not configured')
            except Exception as e:
                last_err = e
                time.sleep(retry.get('backoff_ms', 500)/1000.0)
                attempts += 1
        raise OrchestratorError(str(last_err) if last_err else 'Unknown error')
