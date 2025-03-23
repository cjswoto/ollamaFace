import time
from . import api
from . import search
from . import session as session_manager
from local_retriever import search_index
from kb.kb_manager import load_existing_index


class CoreManager:
    def __init__(self):
        self.ollama_url = "http://localhost:11434"
        self.current_model = None
        self.web_search_enabled = True
        self.search_engine = "DuckDuckGo"
        self.max_search_results = 3
        self.search_timeout = 10
        self.search_debug_info = ""
        self.kb_debug_info = ""
        self.show_web_debug = False
        self.show_kb_debug = False
        self.current_session = None
        self.sessions = session_manager.load_sessions()

        # Load the persistent FAISS index (and associated chunks/metadata) from disk.
        # This index is built and saved by the KB Manager.
        self.kb_index, self.kb_chunks, self.kb_metadata = load_existing_index()

    def get_models(self):
        return api.get_models(self.ollama_url)

    def check_server_connection(self):
        return api.check_server_connection(self.ollama_url)

    def generate_response(self, message, with_search=False, with_local_kb=True):
        search_results = None
        local_results = None
        kb_debug_info = ""

        # 1. Web search retrieval.
        if with_search and self.web_search_enabled:
            search_result_data = search.perform_web_search(
                message, self.search_engine, self.max_search_results, self.search_timeout
            )
            search_results = search_result_data.get("results")
            self.search_debug_info = search_result_data.get("debug")

        # 2. Local KB retrieval from persistent index.
        if with_local_kb:
            if self.kb_index is None or not self.kb_chunks:
                kb_debug_info = "No persistent KB index available."
            else:
                start_time = time.time()
                # Retrieve top 3 matching chunks; note that search_index returns (chunk, distance, metadata)
                local_retrieval = search_index(
                    query=message,
                    index=self.kb_index,
                    chunks=self.kb_chunks,
                    metadata=self.kb_metadata,
                    top_k=3
                )
                elapsed = time.time() - start_time
                if local_retrieval:
                    local_results = "\n".join([f"Chunk: {chunk}" for chunk, _, _ in local_retrieval])
                    # Extract unique document names from metadata.
                    doc_names = {meta.get("filename", "Unknown") for _, _, meta in local_retrieval}
                    kb_debug_info = (
                        f"KB retrieval took {elapsed:.2f} seconds. "
                        f"Retrieved {len(local_retrieval)} chunks from: {', '.join(doc_names)}"
                    )
                else:
                    kb_debug_info = f"KB retrieval took {elapsed:.2f} seconds. No relevant KB content found."

        # Save KB debug info only if enabled.
        if self.show_kb_debug:
            self.kb_debug_info = kb_debug_info
        else:
            self.kb_debug_info = ""

        # 3. Build the prompt.
        prompt = message
        if search_results or local_results:
            prompt = f"""Question: {message}

Local Knowledge Context:
{local_results or "No relevant KB results."}

Web Search Results:
{search_results or "No web search results."}

Please answer the question based on the provided context. If the context isn’t relevant, use your general knowledge to provide the best answer possible."""

        response = api.generate_response(self.ollama_url, self.current_model, prompt)
        return {
            **response,
            "search_results": search_results,
            "kb_debug_info": self.kb_debug_info
        }

    def new_session(self):
        session_id, session_data = session_manager.new_session(self.current_model)
        self.current_session = session_data
        self.sessions[session_id] = session_data
        return session_id

    def load_session(self, session_id):
        session_data = session_manager.load_session(session_id)
        if session_data:
            self.current_session = session_data
            return True
        return False

    def delete_session(self, session_id):
        if session_manager.delete_session(session_id):
            if session_id in self.sessions:
                del self.sessions[session_id]
            if self.current_session and self.current_session.get("id") == session_id:
                self.new_session()
            return True
        return False

    def export_session(self, session_id, file_path):
        session_data = self.sessions.get(session_id)
        if session_data:
            return session_manager.export_session(session_data, file_path)
        return False

    def store_message_in_session(self, role, message):
        if self.current_session:
            session_manager.store_message_in_session(self.current_session, role, message)
