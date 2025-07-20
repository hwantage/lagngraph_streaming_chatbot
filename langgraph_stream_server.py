from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.checkpoint.memory import MemorySaver
import uvicorn
import json

# --- FastAPI 설정 ---
app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 요청 클래스 정의
class QueryRequest(BaseModel):
    query: str
    selected_option: Optional[str] = None
    thread_id: Optional[str] = "chat_111111111111"

# ChatOllama 인스턴스 생성
llm = ChatOllama(
        model="hf.co/MLP-KTLim/llama-3-Korean-Bllossom-8B-gguf-Q4_K_M:Q4_K_M",
        base_url="http://localhost:11434",
        temperature=0
    )

# 시스템 메시지 정의
system_message = SystemMessage(content="You are a helpful AI assistant.")

# MemorySaver checkpointer 생성
memory = MemorySaver()

# LangGraph 노드 함수 정의
async def chatbot(state: MessagesState):
    """LLM을 호출하는 스트리밍 노드"""
    messages = state['messages']

    # 시스템 메시지 추가
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [system_message] + messages

    # 스트리밍 실행 (비동기)
    async for chunk in llm.astream(messages):
        # 각 청크를 yield하여 스트림을 생성합니다.
        yield {"messages": [chunk]}

# StateGraph 구성
workflow = StateGraph(MessagesState)
workflow.add_node("chatbot", chatbot)
workflow.add_edge(START, "chatbot")

# 체크포인터와 함께 그래프 컴파일
graph = workflow.compile(checkpointer=memory)

# 스트리밍 응답 함수
async def stream_rag_response(query: str, thread_id: str, selected_option: Optional[str] = None):
    """
    LangGraph의 astream_events를 활용한 실시간 스트리밍 응답 함수
    """
    try:
        # 사용자 질문 메시지 구성
        if selected_option:
            user_query = f"{query}\n\n추가 요청: {selected_option}"
        else:
            user_query = query

        # 새로운 사용자 메시지 생성
        user_message = HumanMessage(content=user_query)

        # thread config 설정
        config = {"configurable": {"thread_id": thread_id}}

        # 입력 상태 구성
        input_state = {"messages": [user_message]}

        # LangGraph의 비동기 스트리밍 실행
        async for event in graph.astream_events(input_state, config, version="v1"):
            kind = event["event"]
            # 모델이 스트리밍하는 중간 토큰인 경우
            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    # JSON 형식으로 클라이언트에 데이터 전송
                    token_data = {
                        "type": "token",
                        "content": content
                    }
                    yield json.dumps(token_data, ensure_ascii=False) + "\n"

        # 응답 완료 후 고정된 추천 프롬프트 제공
        recommendation_data = {
            "type": "recommendations",
            "data": [
                "더 구체적으로 답변해 주세요.",
                "다른 의견도 듣고 싶어요.",
                "짧게 요약해 주세요."
            ]
        }
        yield json.dumps(recommendation_data, ensure_ascii=False) + "\n"

    except Exception as e:
        # 에러 발생 시 에러 메시지 전송
        error_data = {
            "type": "error",
            "content": f"응답 생성 중 오류가 발생했습니다: {str(e)}"
        }
        yield json.dumps(error_data, ensure_ascii=False) + "\n"

@app.post("/stream-chat")
async def rag_query(request: QueryRequest):
    return StreamingResponse(
        stream_rag_response(request.query, request.thread_id, request.selected_option),
        media_type="text/plain"
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001) 