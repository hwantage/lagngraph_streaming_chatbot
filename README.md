# LangGraph & FastAPI 기반 스트리밍 챗봇 서버

## 개요

이 프로젝트는 [LangGraph](https://python.langchain.com/docs/langgraph)와 [FastAPI](https://fastapi.tiangolo.com/)를 사용하여 구현된 실시간 스트리밍 챗봇 백엔드 서버입니다. 사용자의 질문에 대해 LLM(대규모 언어 모델)이 생성하는 답변을 토큰 단위로 스트리밍하여 실시간 상호작용이 가능한 채팅 경험을 제공합니다. 대화 기록은 LangGraph의 `MemorySaver`를 통해 관리되어 연속적인 대화가 가능합니다.

## 주요 기능

- **FastAPI 기반 비동기 API**: FastAPI를 사용하여 높은 성능의 비동기 웹 서버를 구축했습니다.
- **상태 기반 대화 관리**: LangGraph를 활용하여 대화의 상태를 관리하고, 이를 통해 복잡한 대화 흐름을 제어할 수 있습니다.
- **실시간 응답 스트리밍**: `astream_events` API를 사용하여 LLM이 생성하는 응답을 토큰 단위로 클라이언트에 실시간으로 전송합니다.
- **로컬 LLM 연동**: `langchain-ollama`를 통해 Ollama에서 실행되는 로컬 언어 모델과 쉽게 연동할 수 있습니다.
- **대화 기록 유지**: LangGraph의 `MemorySaver` 체크포인터를 사용하여 `thread_id`별로 대화 기록을 메모리에 저장하고 관리합니다.
- **CORS 지원**: 모든 출처(origin)를 허용하도록 CORS가 설정되어 있어, 어떤 프론트엔드 환경에서도 쉽게 API를 호출할 수 있습니다.

## 사전 요구사항

- Python 3.9 이상
- [Ollama](https://ollama.com/): 로컬 환경에 설치되어 있어야 합니다.
- Ollama 모델: 서버 코드에 명시된 모델(`hf.co/MLP-KTLim/llama-3-Korean-Bllossom-8B-gguf-Q4_K_M:Q4_K_M`)이 로컬에 설치되어 있어야 합니다.
  ```bash
  ollama pull hf.co/MLP-KTLim/llama-3-Korean-Bllossom-8B-gguf-Q4_K_M:Q4_K_M
  ```

## 설치 방법

1.  **프로젝트 클론 (필요시):**
    ```bash
    git clone https://github.com/hwantage/lagngraph_streaming_chatbot.git
    cd lagngraph_streaming_chatbot
    ```

2.  **의존성 패키지 설치:**
    아래 내용을 `requirements.txt` 파일로 저장하고 다음 명령어를 실행하여 필요한 패키지를 설치합니다.
    ```txt
    fastapi
    uvicorn[standard]
    langchain-ollama
    langgraph
    pydantic
    ```
    ```bash
    pip install -r requirements.txt
    ```

## 실행 방법

1.  **Ollama 서버 실행:**
    먼저 로컬 환경에서 Ollama 데스크톱 애플리케이션을 실행하거나, 터미널에서 `ollama serve` 명령을 실행하여 Ollama 서버가 동작 중인지 확인합니다.

2.  **FastAPI 서버 실행:**
    터미널에서 아래 명령어를 실행하여 챗봇봇 서버를 시작합니다.
    ```bash
    python langgraph_stream_server.py
    ```
    서버는 `http://0.0.0.0:8001` 주소에서 실행됩니다.

## API 인터페이스

### `POST /stream-chat`

챗봇에 메시지를 보내고 스트리밍 응답을 받습니다.

-   **요청 본문 (Request Body):** `application/json`

    ```json
    {
      "query": "LangGraph에 대해 설명해줘",
      "selected_option": "짧게 요약해 주세요.",
      "thread_id": "chat_session_12345"
    }
    ```

    -   `query` (str, 필수): 사용자의 질문.
    -   `selected_option` (str, 선택): 추천 프롬프트 등 추가적인 요청 사항.
    -   `thread_id` (str, 선택): 대화를 구분하기 위한 고유 ID입니다. 제공하지 않으면 코드에 명시된 기본값이 사용됩니다. 이 ID를 기준으로 대화 기록이 저장됩니다.

-   **응답 (Response):** `text/plain`

    서버는 스트림 형태로, 개행 문자(`\n`)로 구분된 여러 개의 JSON 객체를 전송합니다.

    -   **토큰 스트리밍:**
        LLM이 답변을 생성하는 동안 `type`이 "token"인 JSON 객체들이 지속적으로 전송됩니다.
        ```json
        {"type": "token", "content": "LangGraph는"}
        {"type": "token", "content": " langchain의"}
        {"type": "token", "content": " 라이브러리로,"}
        ...
        ```

    -   **추천 프롬프트:**
        응답 생성이 완료된 후, 후속 질문으로 사용할 수 있는 추천 목록이 전송됩니다.
        ```json
        {"type": "recommendations", "data": ["더 구체적으로 답변해 주세요.", "다른 의견도 듣고 싶어요.", "짧게 요약해 주세요."]}
        ```

## 코드 구조 설명

-   `langgraph_stream_server.py`:
    -   **FastAPI 설정**: FastAPI 앱 인스턴스(`app`)를 생성하고 모든 도메인에서의 요청을 허용하기 위해 `CORSMiddleware`를 설정합니다.
    -   `QueryRequest`: API 요청의 유효성을 검사하기 위한 Pydantic 모델을 정의합니다.
    -   `ChatOllama`: Ollama에서 실행 중인 로컬 LLM과 통신하기 위한 LangChain 인스턴스를 설정합니다.
    -   `MemorySaver`: LangGraph의 체크포인터로, 대화 상태(메시지 기록)를 메모리에 저장하여 대화의 연속성을 보장합니다.
    -   `StateGraph`: `MessagesState`를 기반으로 대화의 상태 그래프를 정의합니다. `chatbot` 노드를 추가하여 LLM 호출 로직을 그래프에 통합합니다.
    -   `chatbot` (비동기 함수): 현재 대화 상태를 입력받아 시스템 메시지를 추가하고, `llm.astream`을 호출하여 응답을 비동기 스트림으로 생성합니다.
    -   `stream_rag_response` (비동기 함수): 실제 스트리밍 로직을 담당합니다. `graph.astream_events`를 사용하여 LangGraph에서 발생하는 이벤트를 실시간으로 처리하며, `on_chat_model_stream` 이벤트가 발생할 때마다 해당 토큰을 클라이언트로 즉시 전송합니다.
    -   `/stream-chat` 엔드포인트: FastAPI의 `StreamingResponse`를 사용하여 `stream_rag_response` 함수가 생성하는 스트림을 클라이언트에 효율적으로 전달합니다.

## License

MIT