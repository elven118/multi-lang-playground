from services.api.app.ui import build_app


demo = build_app()

if __name__ == "__main__":
    demo.queue().launch()
