import gradio as gr

from services.api.app.ui.styles import load_styles_html
from services.api.app.ui.handlers import (
    fetch_news,
    prepare_loading,
    load_news_history,
    select_item,
    select_saved_item,
    translate_selected_news,
    star_selected_news,
    get_sources,
)


def build_app():
    with gr.Blocks(title="Daily News Learning") as demo:
        gr.HTML(load_styles_html())
        gr.Markdown("# Daily News Learning")

        with gr.Tabs():
            with gr.TabItem("News"):
                # Fetch options
                with gr.Group():
                    def toggle_custom_limit(choice):
                        if choice == "Other: Your custom inputs 1-100":
                            return gr.update(visible=True)
                        return gr.update(visible=False, value="")

                    with gr.Row():
                        fetch_images = gr.Checkbox(
                            value=True,
                            label="Fetch Images (slower)",
                        )
                        limit = gr.Dropdown(
                            choices=[1, 2, 3, 4, 5, 8, 10, 15, 20, "Other: Your custom inputs 1-100"],
                            value=4,
                            label="Items per source",
                            allow_custom_value=False,
                            info="Pick a preset or choose Other to enter a custom value (1-100).",
                        )
                        custom_limit = gr.Textbox(
                            label="Custom items per source (1-100)",
                            placeholder="e.g. 12",
                            visible=False,
                        )
                    with gr.Row():
                        feed_selector = gr.CheckboxGroup(
                            choices=get_sources(),
                            label="News Sources",
                            value=[],
                        )
                        extra_urls = gr.Textbox(
                            label="Custom RSS URLs (one per line)",
                            placeholder="https://example.com/rss.xml",
                            lines=4,
                        )
                fetch_btn = gr.Button("Fetch News")
                status = gr.Textbox(label="Status", interactive=False)
                feed_view = gr.HTML()

                # selected article and translation
                with gr.Group():
                    selected = gr.Dropdown(choices=[], label="Select an article")
                    selected_text = gr.Textbox(lines=6, label="Selected Article")
                    with gr.Row():
                        target_lang = gr.Dropdown(
                            ["繁體中文", "English", "Japanese"],
                            value="繁體中文",
                            label="Target Language",
                        )
                        explain = gr.Checkbox(
                            value=False,
                            label="Add Short Explanation",
                        )
                        add_kana = gr.Checkbox(
                            value=True,
                            label="Add Furigana (Hiragana)",
                        )

                news_items = gr.State([])
                translate_btn = gr.Button("Translate Selected")
                translated = gr.Textbox(lines=8, label="Translation")
                gr.Markdown("**Line-by-Line (Original / Translation)**")
                line_by_line = gr.HTML()
                star_btn = gr.Button("Star & Save")
                star_status = gr.Textbox(label="Save Status", interactive=False)

                limit.change(
                    fn=toggle_custom_limit,
                    inputs=limit,
                    outputs=custom_limit,
                )

                fetch_btn.click(
                    fn=prepare_loading,
                    inputs=[limit],
                    outputs=[feed_view, selected, news_items, status],
                ).then(
                    fn=fetch_news,
                    inputs=[feed_selector, limit, fetch_images, extra_urls, custom_limit],
                    outputs=[feed_view, selected, news_items, status],
                )

                selected.change(
                    fn=select_item,
                    inputs=[selected, news_items],
                    outputs=selected_text,
                )

                translate_btn.click(
                    fn=translate_selected_news,
                    inputs=[selected, news_items, target_lang, explain, add_kana],
                    outputs=[translated, line_by_line],
                )

                star_btn.click(
                    fn=star_selected_news,
                    inputs=[selected, news_items, translated, target_lang, explain],
                    outputs=star_status,
                )

            with gr.TabItem("History"):
                refresh_btn = gr.Button("Refresh History")
                history_view = gr.HTML()
                history_selected = gr.Dropdown(choices=[], label="Select a saved article")
                with gr.Row():
                    history_add_kana = gr.Checkbox(
                        value=True,
                        label="Add Furigana (Hiragana)",
                    )
                history_translated = gr.Textbox(lines=8, label="Saved Translation")
                gr.Markdown("**Line-by-Line (Original / Translation)**")
                history_line_by_line = gr.HTML()
                history_items_state = gr.State([])

                refresh_btn.click(
                    fn=load_news_history,
                    inputs=None,
                    outputs=[history_view, history_selected, history_items_state],
                )

                history_selected.change(
                    fn=select_saved_item,
                    inputs=[history_selected, history_items_state, history_add_kana],
                    outputs=[history_translated, history_line_by_line],
                )

                history_add_kana.change(
                    fn=select_saved_item,
                    inputs=[history_selected, history_items_state, history_add_kana],
                    outputs=[history_translated, history_line_by_line],
                )

    return demo
