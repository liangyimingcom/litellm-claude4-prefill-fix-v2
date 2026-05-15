#!/bin/bash
# AppendContinueCallback v2 — 完整测试矩阵（含生产样例）
# Usage: ./test_live.sh [ENDPOINT] [API_KEY]

ENDPOINT="${1:-https://alblitellm.liangym.people.aws.dev/v1/messages}"
API_KEY="${2:-sk-d0Ja3QFEGY4xoev1_W8FwQ}"
PASS=0; FAIL=0

run() {
    local name="$1" desc="$2" payload="$3"
    local code=$(curl -s -o /dev/null -w "%{http_code}" "$ENDPOINT" \
        -H "x-api-key: $API_KEY" -H "Content-Type: application/json" -H "anthropic-version: 2023-06-01" \
        -d "$payload")
    if [ "$code" = "200" ]; then
        PASS=$((PASS+1)); echo "  ✅ $name ($desc) → HTTP $code"
    else
        FAIL=$((FAIL+1)); echo "  ❌ $name ($desc) → HTTP $code"
    fi
}

echo "═══════════════════════════════════════════════════════════"
echo "  AppendContinueCallback v2 — 完整测试矩阵"
echo "  Endpoint: $ENDPOINT"
echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "═══════════════════════════════════════════════════════════"
echo ""

echo "▶ 基础测试"
run "T1" "正常user结尾" \
  '{"model":"claude-sonnet-4-6","max_tokens":30,"messages":[{"role":"user","content":"Say hi"}]}'
run "T2" "assistant纯文本prefill" \
  '{"model":"claude-sonnet-4-6","max_tokens":50,"messages":[{"role":"user","content":"ECS简介"},{"role":"assistant","content":"Amazon ECS是"}]}'
run "T9" "空assistant消息" \
  '{"model":"claude-sonnet-4-6","max_tokens":30,"messages":[{"role":"user","content":"hello"},{"role":"assistant","content":""}]}'

echo ""
echo "▶ 生产样例 — tool_use(read)"
run "T6a" "text+tool_use(read)" \
  '{"model":"claude-sonnet-4-6","max_tokens":100,"messages":[{"role":"user","content":"读取README"},{"role":"assistant","content":[{"type":"text","text":"先看文件："},{"type":"tool_use","id":"toolu_bdrk_01FBzBarRJVqG2sBeEXddoAK","name":"read","input":{"filePath":"/project/README.md"}}]}]}'
run "T6b" "纯tool_use(read)+offset/limit" \
  '{"model":"claude-sonnet-4-6","max_tokens":100,"messages":[{"role":"user","content":"继续读代码"},{"role":"assistant","content":[{"type":"tool_use","id":"toolu_bdrk_016F8FPHKbKPhj3T6ZDJtYUq","name":"read","input":{"filePath":"/src/views/ytd.vue","offset":340,"limit":110}}]}]}'

echo ""
echo "▶ 生产样例 — tool_use(bash)"
run "T7a" "text+tool_use(bash)" \
  '{"model":"claude-sonnet-4-6","max_tokens":100,"messages":[{"role":"user","content":"计算列宽"},{"role":"assistant","content":[{"type":"text","text":"统计总宽度："},{"type":"tool_use","id":"toolu_bdrk_014TzDJzCpb6umVzG1L8Y2kA","name":"bash","input":{"command":"echo total=1920"}}]}]}'
run "T7b" "纯tool_use(bash)+description" \
  '{"model":"claude-sonnet-4-6","max_tokens":100,"messages":[{"role":"user","content":"查找文件"},{"role":"assistant","content":[{"type":"tool_use","id":"toolu_bdrk_019TGKcnAFcS3VrGEDLceKt3","name":"bash","input":{"command":"ls -la","description":"查看目录"}}]}]}'
run "T7c" "纯tool_use(bash)+timeout+cache_control" \
  '{"model":"claude-sonnet-4-6","max_tokens":100,"messages":[{"role":"user","content":"运行lint"},{"role":"assistant","content":[{"type":"tool_use","id":"toolu_bdrk_017iuoRi6xgMj2gFJpUzk8VM","name":"bash","input":{"command":"echo ok","timeout":30000},"cache_control":{"type":"ephemeral"}}]}]}'

echo ""
echo "▶ 生产样例 — tool_use(todowrite)"
run "T8" "text+tool_use(todowrite)+cache_control" \
  '{"model":"claude-sonnet-4-6","max_tokens":100,"messages":[{"role":"user","content":"规划任务"},{"role":"assistant","content":[{"type":"text","text":"开始改动："},{"type":"tool_use","id":"toolu_bdrk_01EYw7KUFi9HZnLuq1xxzuif","name":"todowrite","input":{"todos":[{"content":"任务A","status":"in_progress","priority":"high"}]},"cache_control":{"type":"ephemeral"}}]}]}'

echo ""
echo "▶ 边界测试"
run "T10" "多个tool_use(2个工具)" \
  '{"model":"claude-sonnet-4-6","max_tokens":100,"messages":[{"role":"user","content":"读两个文件"},{"role":"assistant","content":[{"type":"tool_use","id":"toolu_01A","name":"read","input":{"filePath":"/a.txt"}},{"type":"tool_use","id":"toolu_01B","name":"read","input":{"filePath":"/b.txt"}}]}]}'
run "T12" "多轮对话末尾assistant" \
  '{"model":"claude-sonnet-4-6","max_tokens":50,"messages":[{"role":"user","content":"你好"},{"role":"assistant","content":"你好！"},{"role":"user","content":"ECS是什么"},{"role":"assistant","content":"Amazon ECS是容器服务"}]}'

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  结果: $PASS 通过, $FAIL 失败 (共 $((PASS+FAIL)))"
echo "═══════════════════════════════════════════════════════════"
[ $FAIL -eq 0 ] && echo "  ✅ ALL TESTS PASSED" || echo "  ⚠️ SOME TESTS FAILED"
exit $FAIL
