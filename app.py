import streamlit as st
import pandas as pd
import fitz
import anthropic
import io
import time


def load_file(file):
    if file.type == "text/csv":
        return pd.read_csv(file)
    elif file.type == "text/plain":
        return file.getvalue().decode("utf-8")
    elif file.type == "application/pdf":
        return extract_text_from_pdf(file)
    else:
        st.error("지원하지 않는 파일 형식입니다❎")
        return None


def extract_text_from_pdf(file):
    pdf_file = io.BytesIO(file.getvalue())
    with fitz.open(stream=pdf_file, filetype="pdf") as doc:
        text = ""
        for page in doc:
            text += page.get_text()
    return text


def query_anthropic_model(api_key, system_prompt, messages):
    client = anthropic.Anthropic(api_key=api_key)
    stream = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        system=system_prompt,
        messages=messages,
        max_tokens=4096,
        stream=True
    )
    return stream


def main():
    st.title("파일 내용 질문하기 - Claude Sonnet 3.5")
    st.write("파일을 업로드하고 질문을 입력해주세요.")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "file_upload_time" not in st.session_state:
        st.session_state.file_upload_time = None

    if "uploaded_file" not in st.session_state:
        st.session_state.uploaded_file = None

    api_key = st.text_input("Anthropic API 키:", type="password")

    if api_key:
        st.write("📁 아래 'Browse files' 버튼을 클릭하여 파일을 업로드하세요.")

        if st.session_state.file_upload_time is not None and time.time() - st.session_state.file_upload_time > 600:
            st.warning("⚠️ 세션이 만료되었습니다. 파일을 다시 업로드해주세요.")
            st.session_state.file_upload_time = None
            st.session_state.system_prompt = None
            st.session_state.uploaded_file = None

        uploaded_file = st.file_uploader("CSV, TXT, 또는 PDF 파일 선택", type=["csv", "txt", "pdf"])

        if uploaded_file is not None:
            st.session_state.uploaded_file = uploaded_file
            st.session_state.file_upload_time = time.time()

        if st.session_state.uploaded_file is not None:
            file_content = load_file(st.session_state.uploaded_file)
            if file_content is not None:
                st.success(f"'{st.session_state.uploaded_file.name}' 파일이 성공적으로 업로드되었습니다! ✅")

                if isinstance(file_content, pd.DataFrame):
                    context = file_content.to_csv(index=False)
                else:
                    context = file_content

                st.session_state.system_prompt = f"The following is the content of a file:\n\n{context}"

        if st.session_state.get('system_prompt') is not None:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            if prompt := st.chat_input("파일 내용에 대해 질문하세요"):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):
                    message_placeholder = st.empty()
                    full_response = ""
                    stream = query_anthropic_model(
                        api_key,
                        st.session_state.system_prompt,
                        st.session_state.messages
                    )
                    for chunk in stream:
                        if hasattr(chunk, 'delta') and hasattr(chunk.delta, 'text'):
                            full_response += chunk.delta.text
                            message_placeholder.markdown(full_response + "▌")
                        elif hasattr(chunk, 'content'):
                            full_response += chunk.content
                            message_placeholder.markdown(full_response + "▌")
                    message_placeholder.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
        else:
            st.info("파일을 업로드해주세요.")

    else:
        st.warning("Anthropic API 키를 입력하세요.")


if __name__ == "__main__":
    main()