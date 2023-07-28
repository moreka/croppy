import glob
import io
import subprocess
import tempfile
from os import path
from PIL import Image
import PySimpleGUI as sg
from absl import app, flags
from pypdf import PdfReader, PdfWriter
from pypdf.generic import RectangleObject
from tqdm import tqdm

FLAGS = flags.FLAGS

flags.DEFINE_string("out", None, "output pdf filename")
flags.DEFINE_bool("progress", True, "show conversion progress")
flags.DEFINE_integer("page", 1, "which page to show the gui with")

def main(argv):
    input_pdf_path = argv[1]
    output_pdf_dir = FLAGS.out
    show_progress = FLAGS.progress
    input_pdf_filename = path.basename(input_pdf_path)[:-4]
    default_page = FLAGS.page
   
    if output_pdf_dir is None:
        output_pdf_dir = path.join(path.dirname(input_pdf_path), input_pdf_filename + "-cropped.pdf")
    elif path.isdir(output_pdf_dir):
        output_pdf_dir = path.join(output_pdf_dir, input_pdf_filename + "-cropped.pdf")

    with tempfile.TemporaryDirectory("croppy") as tmpdirname:
        proc = subprocess.Popen(
            f"pdftoppm -f {default_page} -l {default_page} -png {input_pdf_path} {tmpdirname}/{input_pdf_filename}", shell=True
        )
        proc.wait()

        pdf = PdfReader(input_pdf_path)
        pdf_size = (pdf.pages[default_page-1].mediabox.right, pdf.pages[default_page-1].mediabox.top)

        image_filename = glob.glob(tmpdirname + "/*.png")[0]
        img = Image.open(image_filename)
        img = img.resize((img.size[0] // 2, img.size[1] // 2))

        scale = float(pdf_size[0]) / float(img.size[0])

        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format="PNG")
        img_byte_arr = img_byte_arr.getvalue()

        size = (img.size[0], img.size[1])
        layout = [
            [sg.Graph(size, (0, 0), size, enable_events=True, key="-GRAPH-")],
        ]

        window = sg.Window("Title", layout, finalize=True)
        graph = window["-GRAPH-"]
        graph.bind("<ButtonRelease-1>", "+FIN+")
        window.bind("<s>", "+save+")

        x0, y0, x1, y1 = 0, 0, 0, 0

        graph.draw_image(data=img_byte_arr, location=(0, size[1]))
        while True:
            event, values = window.read()
            if event == sg.WIN_CLOSED:
                break
            elif event == "-GRAPH-":
                x0, y0 = values[event]
            elif event == "-GRAPH-+FIN+":
                x1, y1 = values["-GRAPH-"]
                graph.draw_rectangle((x0, y0), (x1, y1), line_color="red")
            elif event == "+save+":
                rect = RectangleObject([x0, y0, x1, y1])
                rect = rect.scale(scale, scale)
                writer = PdfWriter()
                for page in tqdm(pdf.pages) if show_progress else pdf.pages:
                    page.cropbox = rect
                    writer.add_page(page)
                writer.write(output_pdf_dir)
                break
        window.close()


if __name__ == "__main__":
    app.run(main)
