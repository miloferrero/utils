import os
import openai
from base64 import b64encode
import fitz

# Asegúrate de cargar la clave API desde el .env si es necesario
openai.api_key = os.getenv("OPENAI_API_KEY")

def get_gpt_image_response(image_path, prompt):
    """Envía una imagen y un prompt a GPT-4 y obtiene la respuesta."""

    # Lee el archivo de imagen y lo codifica en base64
    with open(image_path, "rb") as image_file:
        image_b64 = b64encode(image_file.read()).decode("utf-8")

    # Envía el prompt y la imagen codificada a GPT-4
    response = openai.OpenAI().chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                    },
                ],
            }
        ],
    )

    # Extrae y retorna la respuesta
    answer = response.choices[0].message.content
    return answer
    
def view(image_path, prompt):
    """Verifica la existencia del archivo de imagen y obtiene la respuesta de GPT-4."""
    if os.path.exists(image_path):
        print("Enviando la imagen y el prompt a GPT-4...")
        answer = get_gpt_image_response(image_path, prompt)
        #print("Respuesta de GPT-4:", answer)
        return answer  # Devuelve la respuesta obtenida
    else:
        print("La ruta de la imagen no es válida o el archivo no existe.")
        return None  # Devuelve None si el archivo no existe

def document_enrichment(input_pdf, output_pdf, prompt):
    """
    Processes a PDF file, extracts text, and appends image descriptions at the end of each page.
    Args:
        input_pdf (str): Path to the input PDF.
        output_pdf (str): Path to the output PDF with descriptions.
        prompt (str): Prompt for describing images.
    """
    # Ensure the ./temp directory exists
    temp_dir = "./temp"
    os.makedirs(temp_dir, exist_ok=True)

    try:
        # Open the input PDF
        pdf_document = fitz.open(input_pdf)
    except Exception as e:
        print(f"Error opening input PDF: {e}")
        return

    try:
        # Create a new PDF for output
        output_document = fitz.open()

        for page_num in range(len(pdf_document)):
            try:
                # Process each page
                page = pdf_document[page_num]

                # Extract text content
                text = page.get_text("text") or "No text found on this page."

                # Create a new page in the output PDF
                output_page = output_document.new_page(width=page.rect.width, height=page.rect.height)

                # Write the extracted text to the new page
                y_position = 72  # Start with a 1-inch margin from the top
                line_height = 12 + 4  # Font size plus spacing

                for line in text.splitlines():
                    output_page.insert_text((72, y_position), line, fontsize=12)
                    y_position += line_height

                # Process images on the page
                images = page.get_images(full=True)
                if images:
                    description_y_position = y_position + line_height * 2  # Space before descriptions
                    output_page.insert_text((72, description_y_position), "Image Descriptions:", fontsize=12, color=(0, 0, 1))
                    description_y_position += line_height * 2

                    for img_index, img in enumerate(images):
                        try:
                            # Get the image XREF (cross-reference) number
                            xref = img[0]

                            # Extract the image bytes
                            base_image = pdf_document.extract_image(xref)
                            image_bytes = base_image["image"]
                            image_path = os.path.join(temp_dir, f"temp_image_{page_num}_{img_index}.png")

                            # Save the image temporarily
                            with open(image_path, "wb") as img_file:
                                img_file.write(image_bytes)

                            # Use the view function to generate a description for the image
                            answer = view(image_path, prompt)

                            # Wrap long text for image description based on an approximate character limit
                            max_chars_per_line = 80  # Adjust based on font size and page width
                            words = answer.split()
                            current_line = ""
                            for word in words:
                                test_line = f"{current_line} {word}".strip()
                                if len(test_line) <= max_chars_per_line:
                                    current_line = test_line
                                else:
                                    output_page.insert_text((72, description_y_position), current_line, fontsize=12)
                                    description_y_position += line_height
                                    current_line = word  # Start new line with current word
                            # Insert any remaining text in the current line
                            if current_line:
                                output_page.insert_text((72, description_y_position), current_line, fontsize=12)
                                description_y_position += line_height * 2  # Extra space after each description

                            # Clean up the temporary image file
                            os.remove(image_path)

                        except Exception as img_error:
                            print(f"Error processing image {img_index} on page {page_num}: {img_error}")

            except Exception as page_error:
                print(f"Error processing page {page_num}: {page_error}")

        # Save the output PDF
        output_document.save(output_pdf)
        print(f"Processed PDF saved as {output_pdf}")

    except Exception as e:
        print(f"Error processing PDF: {e}")

    finally:
        # Close documents
        pdf_document.close()
        output_document.close()
