import streamlit as st

def page_config():
    page_1 = st.Page(
        page="pages/page_1.py",
        title="How relevant is PLTV for you?",
        default=True,
    )
    page_2 = st.Page(
        page="pages/page_2.py",
        title="Short to long-term overall revenue correlation",
    )
    page_3 = st.Page(
        page="pages/page_3.py",
        title="Post-Optimization Conversions",
    )
    page_4 = st.Page(
        page="pages/page_4.py",
        title="User Value Re-Ranking",
    )
    return [page_1, page_2, page_3, page_4]

def setup_navigation(pages):
    pg = st.navigation(
        {
            "Main": [pages[0]],
            "Plots": pages[1:],
        }
    )
    return pg

def main():
    pages = page_config()
    pg = setup_navigation(pages)
    pg.run()

if __name__ == "__main__":
    main()


