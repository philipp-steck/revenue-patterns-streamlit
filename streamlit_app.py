import streamlit as st


def page_config():
    page_1 = st.Page(
        page="pages/page_1.py",
        title="Data Extraction Helper and Upload",
        default=True,
        # icon=":material/build:"
    )
    page_2 = st.Page(
        page="pages/page_2.py",
        title="Revenue Correlation",
        # icon=":material/analytics:"
    )
    page_3 = st.Page(
        page="pages/page_3.py",
        title="Post-Optimization Conversions",
        # icon=":material/timeline:"
    )
    page_4 = st.Page(
        page="pages/page_4.py",
        title="User Value Re-Ranking",
        # icon=":material/analytics:"
    )
    page_5 = st.Page(
        page="pages/page_5.py",
        title="Estimated Monetary Lift",
        # icon=":material/analytics:"
    )
    return [page_1, page_2, page_3, page_4, page_5]


def setup_navigation(pages):
    pg = st.navigation(
        {
            "Setup": [pages[0]],
            "Analysis": pages[1:],
        }
    )
    return pg


def main():
    pages = page_config()
    pg = setup_navigation(pages)
    pg.run()


if __name__ == "__main__":
    main()
